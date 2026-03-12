from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth import get_current_user
from app.db import get_db
from app.models import Opportunity, PipelineComment, PipelineEntry, User
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
        .options(
            joinedload(PipelineEntry.opportunity).joinedload(Opportunity.analysis),
            joinedload(PipelineEntry.pipeline_comments),
        )
        .order_by(PipelineEntry.position, PipelineEntry.priority.desc(), PipelineEntry.created_at)
    )
    entries = result.unique().scalars().all()

    grouped = {stage: [] for stage in STAGES}
    for entry in entries:
        stage = entry.stage if entry.stage in STAGES else "found"
        data = PipelineEntryResponse.model_validate(entry).model_dump()
        data["comment_count"] = len(entry.pipeline_comments) if entry.pipeline_comments else 0
        grouped[stage].append(data)

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

    # Get max position for the stage
    max_pos = await db.execute(
        select(func.max(PipelineEntry.position)).where(PipelineEntry.stage == body.stage)
    )
    next_pos = (max_pos.scalar() or 0) + 1

    entry = PipelineEntry(
        opportunity_id=body.opportunity_id,
        stage=body.stage,
        notes=body.notes,
        priority=body.priority,
        position=next_pos,
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


class MoveRequest(BaseModel):
    stage: str
    position: int


@router.put("/{entry_id}/move")
async def move_pipeline_entry(
    entry_id: str,
    body: MoveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(PipelineEntry).where(PipelineEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Pipeline entry not found")

    old_stage = entry.stage
    entry.stage = body.stage
    entry.position = body.position

    if old_stage != body.stage:
        history = list(entry.history or [])
        history.append({
            "from": old_stage,
            "to": body.stage,
            "by": str(user.id),
            "notes": "Moved via drag-and-drop",
            "at": datetime.now(timezone.utc).isoformat(),
        })
        entry.history = history

    await db.flush()
    return {"status": "ok"}


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


# --- Comments ---

class PipelineCommentCreate(BaseModel):
    content: str


@router.get("/{entry_id}/comments")
async def list_pipeline_comments(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PipelineComment)
        .where(PipelineComment.pipeline_entry_id == entry_id)
        .order_by(PipelineComment.created_at)
    )
    comments = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "user_id": str(c.user_id),
            "content": c.content,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in comments
    ]


@router.post("/{entry_id}/comments")
async def add_pipeline_comment(
    entry_id: str,
    body: PipelineCommentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = PipelineComment(
        pipeline_entry_id=entry_id,
        user_id=user.id,
        content=body.content,
    )
    db.add(comment)
    await db.flush()
    return {
        "id": str(comment.id),
        "user_id": str(comment.user_id),
        "content": comment.content,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


@router.delete("/{entry_id}/comments/{comment_id}")
async def delete_pipeline_comment(
    entry_id: str,
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PipelineComment).where(
            PipelineComment.id == comment_id,
            PipelineComment.pipeline_entry_id == entry_id,
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    await db.delete(comment)
    return {"status": "deleted"}
