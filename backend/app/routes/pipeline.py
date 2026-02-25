from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth import get_current_user
from app.db import get_db
from app.models import Opportunity, PipelineEntry, User
from app.schemas import PipelineEntryCreate, PipelineEntryResponse, PipelineEntryUpdate

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

STAGES = ["found", "reviewing", "pursuing", "applied", "won", "lost", "archived"]


@router.get("")
async def get_pipeline(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PipelineEntry)
        .options(joinedload(PipelineEntry.opportunity).joinedload(Opportunity.analysis))
        .order_by(PipelineEntry.priority.desc(), PipelineEntry.created_at)
    )
    entries = result.unique().scalars().all()

    grouped = {stage: [] for stage in STAGES}
    for entry in entries:
        stage = entry.stage if entry.stage in STAGES else "found"
        grouped[stage].append(PipelineEntryResponse.model_validate(entry))

    return grouped


@router.post("", response_model=PipelineEntryResponse)
async def add_to_pipeline(
    body: PipelineEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Check opp exists
    opp_result = await db.execute(select(Opportunity).where(Opportunity.id == body.opportunity_id))
    if not opp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Check not already in pipeline
    existing = await db.execute(
        select(PipelineEntry).where(PipelineEntry.opportunity_id == body.opportunity_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already in pipeline")

    entry = PipelineEntry(
        opportunity_id=body.opportunity_id,
        stage=body.stage,
        notes=body.notes,
        priority=body.priority,
        history=[{
            "from": None,
            "to": body.stage,
            "by": str(user.id),
            "notes": "Added to pipeline",
            "at": datetime.now(timezone.utc).isoformat(),
        }],
    )
    db.add(entry)
    await db.flush()
    return PipelineEntryResponse.model_validate(entry)


@router.put("/{entry_id}", response_model=PipelineEntryResponse)
async def update_pipeline_entry(
    entry_id: str,
    body: PipelineEntryUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(PipelineEntry).where(PipelineEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Pipeline entry not found")

    update_data = body.model_dump(exclude_unset=True)

    if "stage" in update_data and update_data["stage"] != entry.stage:
        history = list(entry.history or [])
        history.append({
            "from": entry.stage,
            "to": update_data["stage"],
            "by": str(user.id),
            "notes": update_data.get("notes", ""),
            "at": datetime.now(timezone.utc).isoformat(),
        })
        entry.history = history

    for key, value in update_data.items():
        setattr(entry, key, value)

    await db.flush()
    return PipelineEntryResponse.model_validate(entry)


@router.delete("/{entry_id}")
async def delete_pipeline_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(PipelineEntry).where(PipelineEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Pipeline entry not found")

    await db.delete(entry)
    return {"status": "deleted"}


@router.get("/stats")
async def pipeline_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PipelineEntry.stage, func.count(PipelineEntry.id))
        .group_by(PipelineEntry.stage)
    )
    counts = {row[0]: row[1] for row in result.all()}
    return {stage: counts.get(stage, 0) for stage in STAGES}
