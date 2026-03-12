import asyncio
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, desc, asc, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth import get_current_user
from app.db import get_db
from app.models import Opportunity, OpportunityAnalysis, PipelineEntry, User
from app.schemas import OpportunityResponse, PaginatedResponse

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=PaginatedResponse)
async def list_opportunities(
    search: str | None = None,
    source: str | None = None,
    naics_code: str | None = None,
    min_relevancy: float | None = None,
    set_aside_type: str | None = None,
    state: str | None = None,
    posted_after: str | None = None,
    posted_before: str | None = None,
    deadline_after: str | None = None,
    deadline_before: str | None = None,
    is_active: bool | None = None,
    sort_by: str = "posted_date",
    sort_dir: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Opportunity).options(
        joinedload(Opportunity.analysis),
        joinedload(Opportunity.pipeline_entry),
    )

    if search:
        # Use full-text search if search_vector column exists, fallback to ILIKE
        try:
            ts_query = func.plainto_tsquery('english', search)
            query = query.where(
                Opportunity.search_vector.op('@@')(ts_query)
            ).order_by(
                func.ts_rank(Opportunity.search_vector, ts_query).desc()
            )
        except Exception:
            query = query.where(
                or_(
                    Opportunity.title.ilike(f"%{search}%"),
                    Opportunity.description.ilike(f"%{search}%"),
                    Opportunity.solicitation_number.ilike(f"%{search}%"),
                    Opportunity.agency.ilike(f"%{search}%"),
                )
            )
    if source:
        query = query.where(Opportunity.source == source)
    if naics_code:
        query = query.where(Opportunity.naics_code == naics_code)
    if set_aside_type:
        query = query.where(Opportunity.set_aside_type == set_aside_type)
    if state:
        query = query.where(Opportunity.place_of_performance_state == state)
    if posted_after:
        query = query.where(Opportunity.posted_date >= posted_after)
    if posted_before:
        query = query.where(Opportunity.posted_date <= posted_before)
    if deadline_after:
        query = query.where(Opportunity.response_deadline >= deadline_after)
    if deadline_before:
        query = query.where(Opportunity.response_deadline <= deadline_before)
    if is_active is not None:
        query = query.where(Opportunity.is_active == is_active)
    if min_relevancy is not None:
        query = query.join(OpportunityAnalysis).where(
            OpportunityAnalysis.relevancy_score >= min_relevancy
        )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Sort
    sort_col = getattr(Opportunity, sort_by, Opportunity.posted_date)
    query = query.order_by(desc(sort_col) if sort_dir == "desc" else asc(sort_col))

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = result.unique().scalars().all()

    return PaginatedResponse(
        items=[OpportunityResponse.model_validate(o) for o in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{opp_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opp_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Opportunity)
        .options(
            joinedload(Opportunity.analysis),
            joinedload(Opportunity.pipeline_entry),
        )
        .where(Opportunity.id == opp_id)
    )
    opp = result.unique().scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return OpportunityResponse.model_validate(opp)


@router.post("/{opp_id}/analyze")
async def trigger_analysis(
    opp_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Opportunity).where(Opportunity.id == opp_id))
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Create or reset analysis record
    analysis_result = await db.execute(
        select(OpportunityAnalysis).where(OpportunityAnalysis.opportunity_id == opp_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if analysis:
        analysis.status = "pending"
        analysis.error_message = None
    else:
        from app.models import CompanyProfile
        company_result = await db.execute(select(CompanyProfile).limit(1))
        company = company_result.scalar_one_or_none()
        analysis = OpportunityAnalysis(
            opportunity_id=opp.id,
            company_id=company.id if company else None,
            status="pending",
        )
        db.add(analysis)
    await db.flush()

    # Launch background analysis
    from app.ai.analyzer import run_analysis_task
    asyncio.create_task(run_analysis_task(str(opp.id)))

    return {"status": "analysis_queued", "opportunity_id": str(opp.id)}


@router.post("/{opp_id}/parse-documents")
async def trigger_parse_documents(
    opp_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Opportunity).where(Opportunity.id == opp_id))
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Launch background document parsing
    asyncio.create_task(_parse_documents_task(str(opp.id)))
    return {"status": "parse_queued", "opportunity_id": str(opp.id)}


async def _parse_documents_task(opportunity_id: str):
    """Background task to download and parse opportunity documents."""
    from app.db import async_session
    from app.services.document_parser import download_and_parse_document

    async with async_session() as db:
        try:
            result = await db.execute(
                select(Opportunity).where(Opportunity.id == opportunity_id)
            )
            opp = result.scalar_one_or_none()
            if not opp or not opp.documents:
                return

            updated_docs = []
            for doc in opp.documents:
                if not isinstance(doc, dict):
                    continue
                url = doc.get("url")
                filename = doc.get("filename", "unknown")
                if url:
                    parsed = await download_and_parse_document(url, filename)
                    updated_docs.append({**doc, **parsed})
                else:
                    updated_docs.append({**doc, "parse_status": "no_url"})

            opp.documents = updated_docs
            await db.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Document parsing failed for {opportunity_id}: {e}")
