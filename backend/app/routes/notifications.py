from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import NotificationLog, NotificationRule, User
from app.schemas import (
    NotificationLogResponse,
    NotificationRuleCreate,
    NotificationRuleResponse,
    NotificationRuleUpdate,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/rules", response_model=list[NotificationRuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(NotificationRule).where(NotificationRule.user_id == user.id)
    )
    return [NotificationRuleResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/rules", response_model=NotificationRuleResponse)
async def create_rule(
    body: NotificationRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rule = NotificationRule(user_id=user.id, **body.model_dump())
    db.add(rule)
    await db.flush()
    return NotificationRuleResponse.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=NotificationRuleResponse)
async def update_rule(
    rule_id: str,
    body: NotificationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(NotificationRule).where(
            NotificationRule.id == rule_id, NotificationRule.user_id == user.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    await db.flush()
    return NotificationRuleResponse.model_validate(rule)


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(NotificationRule).where(
            NotificationRule.id == rule_id, NotificationRule.user_id == user.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    return {"status": "deleted"}


@router.get("/log", response_model=list[NotificationLogResponse])
async def notification_log(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.user_id == user.id)
        .order_by(desc(NotificationLog.created_at))
        .limit(100)
    )
    return [NotificationLogResponse.model_validate(n) for n in result.scalars().all()]
