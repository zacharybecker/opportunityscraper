from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import InAppNotification, User

router = APIRouter(prefix="/notifications/inbox", tags=["inbox"])


@router.get("")
async def get_inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        select(InAppNotification)
        .where(InAppNotification.user_id == user.id)
        .order_by(desc(InAppNotification.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "body": n.body,
            "category": n.category,
            "link": n.link,
            "is_read": n.is_read,
            "opportunity_id": str(n.opportunity_id) if n.opportunity_id else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in items
    ]


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(func.count(InAppNotification.id)).where(
            InAppNotification.user_id == user.id,
            InAppNotification.is_read == False,
        )
    )
    count = result.scalar() or 0
    return {"count": count}


@router.put("/{notif_id}/read")
async def mark_read(
    notif_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(InAppNotification).where(
            InAppNotification.id == notif_id,
            InAppNotification.user_id == user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    return {"status": "ok"}


@router.post("/mark-all-read")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await db.execute(
        update(InAppNotification)
        .where(
            InAppNotification.user_id == user.id,
            InAppNotification.is_read == False,
        )
        .values(is_read=True)
    )
    return {"status": "ok"}


@router.delete("/{notif_id}")
async def delete_notification(
    notif_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(InAppNotification).where(
            InAppNotification.id == notif_id,
            InAppNotification.user_id == user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(notif)
    return {"status": "deleted"}
