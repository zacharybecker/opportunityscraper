import asyncio
import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_role
from app.db import get_db
from app.models import CompanyProfile, Opportunity, OpportunityAnalysis, User

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


class ManualOpportunityRequest(BaseModel):
    title: str
    description: str | None = None
    agency: str | None = None
    solicitation_number: str | None = None
    naics_code: str | None = None
    set_aside_type: str | None = None
    response_deadline: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    place_of_performance_state: str | None = None
    place_of_performance_city: str | None = None
    notice_type: str | None = None
    source_url: str | None = None


@router.post("/manual")
async def create_manual_opportunity(
    body: ManualOpportunityRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("analyst")),
):
    content_hash = hashlib.sha256(f"{body.title}{body.description or ''}".encode()).hexdigest()
    external_id = f"manual-{uuid.uuid4().hex[:12]}"

    deadline = None
    if body.response_deadline:
        try:
            deadline = datetime.fromisoformat(body.response_deadline.replace("Z", "+00:00"))
        except ValueError:
            pass

    opp = Opportunity(
        external_id=external_id,
        source="manual",
        source_url=body.source_url,
        title=body.title,
        description=body.description,
        agency=body.agency,
        solicitation_number=body.solicitation_number,
        naics_code=body.naics_code,
        set_aside_type=body.set_aside_type,
        response_deadline=deadline,
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        place_of_performance_state=body.place_of_performance_state,
        place_of_performance_city=body.place_of_performance_city,
        notice_type=body.notice_type,
        posted_date=datetime.now(timezone.utc),
        content_hash=content_hash,
        is_active=True,
    )
    db.add(opp)
    await db.flush()

    return {"id": str(opp.id), "status": "created"}


@router.post("/upload")
async def upload_opportunity(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("analyst")),
):
    from app.services.document_parser import extract_text

    content = await file.read()
    text = extract_text(file.filename or "file", content)

    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from document")

    # Use AI to extract fields
    from app.ai.extractor import extract_opportunity_from_text
    extracted = await extract_opportunity_from_text(text)

    if not extracted.get("title"):
        extracted["title"] = file.filename or "Uploaded Opportunity"

    content_hash = hashlib.sha256(text[:5000].encode()).hexdigest()
    external_id = f"upload-{uuid.uuid4().hex[:12]}"

    deadline = None
    if extracted.get("response_deadline"):
        try:
            deadline = datetime.fromisoformat(extracted["response_deadline"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    opp = Opportunity(
        external_id=external_id,
        source="manual",
        title=extracted.get("title", "Uploaded Opportunity"),
        description=extracted.get("description") or text[:5000],
        agency=extracted.get("agency"),
        solicitation_number=extracted.get("solicitation_number"),
        naics_code=extracted.get("naics_code"),
        set_aside_type=extracted.get("set_aside_type"),
        response_deadline=deadline,
        contact_name=extracted.get("contact_name"),
        contact_email=extracted.get("contact_email"),
        contact_phone=extracted.get("contact_phone"),
        place_of_performance_state=extracted.get("place_of_performance_state"),
        place_of_performance_city=extracted.get("place_of_performance_city"),
        notice_type=extracted.get("notice_type"),
        posted_date=datetime.now(timezone.utc),
        content_hash=content_hash,
        is_active=True,
    )
    db.add(opp)
    await db.flush()

    # Auto-trigger analysis
    company_result = await db.execute(select(CompanyProfile).limit(1))
    company = company_result.scalar_one_or_none()
    if company:
        analysis = OpportunityAnalysis(
            opportunity_id=opp.id,
            company_id=company.id,
            status="pending",
        )
        db.add(analysis)
        await db.flush()

        from app.ai.analyzer import run_analysis_task
        asyncio.create_task(run_analysis_task(str(opp.id)))

    return {
        "id": str(opp.id),
        "status": "created",
        "extracted_fields": extracted,
    }
