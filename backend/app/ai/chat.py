import json
import logging
from typing import AsyncIterator

from sqlalchemy import select, desc, func, or_
from sqlalchemy.orm import joinedload

from app.ai.client import chat_completion_stream
from app.db import async_session
from app.models import ChatSession, Opportunity, OpportunityAnalysis, PipelineEntry

logger = logging.getLogger(__name__)


async def chat_respond(session_id: str, user_message: str) -> AsyncIterator[str]:
    """Process a user message and stream back a response with RAG context."""
    async with async_session() as db:
        # Get session context
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            yield "Session not found."
            return

        # Get recent messages for context
        messages = session.messages or []
        recent_messages = messages[-10:]

        # Classify intent and gather context
        context = await gather_context(db, user_message)

        # Build system message with context
        system_msg = """You are an AI assistant for a government procurement opportunity tracking system.
You help users find and analyze government RFPs/RFQs, understand their pipeline, and make decisions about which opportunities to pursue.

You have access to the following data context:
"""
        if context:
            system_msg += f"\n{context}\n"

        system_msg += """
When referencing specific opportunities, include their title and solicitation number if available.
Be concise and actionable in your responses. If asked about specific data, reference the context provided."""

        # Build conversation
        ai_messages = [{"role": "system", "content": system_msg}]
        for msg in recent_messages:
            if isinstance(msg, dict):
                ai_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })
        ai_messages.append({"role": "user", "content": user_message})

        # Stream response
        async for token in chat_completion_stream(ai_messages):
            yield token


async def gather_context(db, user_message: str) -> str:
    """Gather relevant database context for the chat response."""
    context_parts = []
    msg_lower = user_message.lower()

    # Search for relevant opportunities
    if any(kw in msg_lower for kw in ["opportunity", "opportunities", "rfp", "rfq", "solicitation", "contract", "find", "search"]):
        # Extract potential search terms (simple keyword extraction)
        search_terms = [
            w for w in user_message.split()
            if len(w) > 3 and w.lower() not in {"what", "which", "show", "find", "about", "with", "that", "this", "from", "have", "opportunities", "opportunity"}
        ]

        query = select(Opportunity).options(
            joinedload(Opportunity.analysis)
        ).where(Opportunity.is_active == True)

        if search_terms:
            conditions = []
            for term in search_terms[:3]:
                conditions.append(Opportunity.title.ilike(f"%{term}%"))
                conditions.append(Opportunity.description.ilike(f"%{term}%"))
                conditions.append(Opportunity.agency.ilike(f"%{term}%"))
            query = query.where(or_(*conditions))

        query = query.order_by(desc(Opportunity.posted_date)).limit(10)
        result = await db.execute(query)
        opps = result.unique().scalars().all()

        if opps:
            context_parts.append(f"Found {len(opps)} relevant opportunities:")
            for opp in opps:
                line = f"- {opp.title}"
                if opp.solicitation_number:
                    line += f" ({opp.solicitation_number})"
                if opp.agency:
                    line += f" | Agency: {opp.agency}"
                if opp.analysis and opp.analysis.relevancy_score:
                    line += f" | Relevancy: {opp.analysis.relevancy_score}%"
                if opp.response_deadline:
                    line += f" | Deadline: {opp.response_deadline.strftime('%Y-%m-%d')}"
                context_parts.append(line)

    # Pipeline info
    if any(kw in msg_lower for kw in ["pipeline", "status", "tracking", "pursuing", "applied", "won"]):
        pipeline_result = await db.execute(
            select(PipelineEntry.stage, func.count(PipelineEntry.id))
            .group_by(PipelineEntry.stage)
        )
        counts = {row[0]: row[1] for row in pipeline_result.all()}
        if counts:
            context_parts.append(f"\nPipeline Status: {json.dumps(counts)}")

        # Recent pipeline entries
        recent = await db.execute(
            select(PipelineEntry)
            .options(joinedload(PipelineEntry.opportunity))
            .order_by(desc(PipelineEntry.updated_at))
            .limit(5)
        )
        entries = recent.unique().scalars().all()
        if entries:
            context_parts.append("Recent pipeline entries:")
            for e in entries:
                opp_title = e.opportunity.title if e.opportunity else "Unknown"
                context_parts.append(f"- {opp_title} | Stage: {e.stage} | Priority: {e.priority}")

    # High relevancy info
    if any(kw in msg_lower for kw in ["relevant", "relevancy", "best", "top", "recommended", "high"]):
        high_rel = await db.execute(
            select(Opportunity)
            .join(OpportunityAnalysis)
            .options(joinedload(Opportunity.analysis))
            .where(OpportunityAnalysis.relevancy_label == "high")
            .order_by(desc(OpportunityAnalysis.relevancy_score))
            .limit(5)
        )
        top_opps = high_rel.unique().scalars().all()
        if top_opps:
            context_parts.append("\nTop relevant opportunities:")
            for opp in top_opps:
                score = opp.analysis.relevancy_score if opp.analysis else "N/A"
                context_parts.append(f"- {opp.title} | Score: {score} | Agency: {opp.agency or 'N/A'}")

    # Deadline info
    if any(kw in msg_lower for kw in ["deadline", "due", "expiring", "upcoming", "soon"]):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        deadlines = await db.execute(
            select(Opportunity)
            .where(
                Opportunity.is_active == True,
                Opportunity.response_deadline.isnot(None),
                Opportunity.response_deadline >= now,
            )
            .order_by(Opportunity.response_deadline)
            .limit(10)
        )
        upcoming = deadlines.scalars().all()
        if upcoming:
            context_parts.append("\nUpcoming deadlines:")
            for opp in upcoming:
                days_left = (opp.response_deadline - now).days
                context_parts.append(
                    f"- {opp.title} | Deadline: {opp.response_deadline.strftime('%Y-%m-%d')} ({days_left} days)"
                )

    return "\n".join(context_parts)
