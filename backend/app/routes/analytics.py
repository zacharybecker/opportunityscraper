from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import (
    Opportunity,
    OpportunityAnalysis,
    PipelineEntry,
    ScrapeRun,
    User,
)
from app.schemas import DashboardResponse, OpportunityResponse, ScrapeRunResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)

    # Active opps
    active_count = (await db.execute(
        select(func.count(Opportunity.id)).where(Opportunity.is_active == True)
    )).scalar() or 0

    # High relevancy
    high_rel = (await db.execute(
        select(func.count(OpportunityAnalysis.id)).where(
            OpportunityAnalysis.relevancy_label == "high"
        )
    )).scalar() or 0

    # Approaching deadlines (next 7 days)
    deadline_count = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.is_active == True,
            Opportunity.response_deadline.isnot(None),
            Opportunity.response_deadline >= now,
            Opportunity.response_deadline <= now + timedelta(days=7),
        )
    )).scalar() or 0

    # Pipeline counts
    pipeline_result = await db.execute(
        select(PipelineEntry.stage, func.count(PipelineEntry.id))
        .group_by(PipelineEntry.stage)
    )
    pipeline_counts = {row[0]: row[1] for row in pipeline_result.all()}

    # Recent high relevancy
    from sqlalchemy.orm import joinedload
    high_rel_result = await db.execute(
        select(Opportunity)
        .join(OpportunityAnalysis)
        .options(joinedload(Opportunity.analysis), joinedload(Opportunity.pipeline_entry))
        .where(OpportunityAnalysis.relevancy_label == "high")
        .order_by(desc(Opportunity.posted_date))
        .limit(10)
    )
    recent_high = [OpportunityResponse.model_validate(o) for o in high_rel_result.unique().scalars().all()]

    # Upcoming deadlines
    deadline_result = await db.execute(
        select(Opportunity)
        .options(joinedload(Opportunity.analysis), joinedload(Opportunity.pipeline_entry))
        .where(
            Opportunity.is_active == True,
            Opportunity.response_deadline.isnot(None),
            Opportunity.response_deadline >= now,
        )
        .order_by(Opportunity.response_deadline)
        .limit(10)
    )
    upcoming = [OpportunityResponse.model_validate(o) for o in deadline_result.unique().scalars().all()]

    # Recent scrape runs
    runs_result = await db.execute(
        select(ScrapeRun).order_by(desc(ScrapeRun.created_at)).limit(10)
    )
    recent_runs = [ScrapeRunResponse.model_validate(r) for r in runs_result.scalars().all()]

    return DashboardResponse(
        active_opportunities=active_count,
        high_relevancy_count=high_rel,
        approaching_deadlines=deadline_count,
        pipeline_counts=pipeline_counts,
        recent_high_relevancy=recent_high,
        upcoming_deadlines=upcoming,
        recent_scrape_runs=recent_runs,
    )


@router.get("/charts")
async def charts(
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    # Relevancy distribution
    rel_dist = await db.execute(
        select(OpportunityAnalysis.relevancy_label, func.count(OpportunityAnalysis.id))
        .where(OpportunityAnalysis.status == "completed")
        .group_by(OpportunityAnalysis.relevancy_label)
    )
    relevancy_distribution = [{"label": r[0], "count": r[1]} for r in rel_dist.all()]

    # Top NAICS
    naics_result = await db.execute(
        select(Opportunity.naics_code, func.count(Opportunity.id))
        .where(Opportunity.naics_code.isnot(None), Opportunity.created_at >= since)
        .group_by(Opportunity.naics_code)
        .order_by(desc(func.count(Opportunity.id)))
        .limit(10)
    )
    top_naics = [{"code": r[0], "count": r[1]} for r in naics_result.all()]

    # Pipeline velocity (avg days per stage)
    pipeline_result = await db.execute(
        select(PipelineEntry.stage, func.count(PipelineEntry.id))
        .group_by(PipelineEntry.stage)
    )
    pipeline_data = [{"stage": r[0], "count": r[1]} for r in pipeline_result.all()]

    # Win rate
    won = (await db.execute(
        select(func.count(PipelineEntry.id)).where(PipelineEntry.stage == "won")
    )).scalar() or 0
    total_decided = (await db.execute(
        select(func.count(PipelineEntry.id)).where(PipelineEntry.stage.in_(["won", "lost"]))
    )).scalar() or 0
    win_rate = (won / total_decided * 100) if total_decided > 0 else 0

    return {
        "relevancy_distribution": relevancy_distribution,
        "top_naics": top_naics,
        "pipeline_data": pipeline_data,
        "win_rate": round(win_rate, 1),
        "total_decided": total_decided,
    }
