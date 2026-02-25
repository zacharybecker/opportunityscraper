import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db, async_session
from app.models import ChatSession, User
from app.schemas import ChatMessageRequest, ChatSessionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(desc(ChatSession.updated_at))
    )
    return [ChatSessionResponse.model_validate(s) for s in result.scalars().all()]


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = ChatSession(user_id=user.id, title="New Chat", messages=[])
    db.add(session)
    await db.flush()
    return ChatSessionResponse.model_validate(session)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    return {"status": "deleted"}


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    body: ChatMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Add user message
    messages = list(session.messages or [])
    messages.append({
        "role": "user",
        "content": body.content,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    session.messages = messages
    await db.commit()

    async def stream_response():
        try:
            from app.ai.chat import chat_respond
            full_response = ""
            async for token in chat_respond(str(session_id), body.content):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"

            # Save assistant message
            async with async_session() as save_db:
                res = await save_db.execute(
                    select(ChatSession).where(ChatSession.id == session_id)
                )
                sess = res.scalar_one()
                msgs = list(sess.messages or [])
                msgs.append({
                    "role": "assistant",
                    "content": full_response,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                sess.messages = msgs
                await save_db.commit()

            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")
