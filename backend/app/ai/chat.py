import json
import logging
from typing import AsyncIterator

from sqlalchemy import select, desc, func, or_
from sqlalchemy.orm import joinedload

from app.ai.client import chat_completion_stream
from app.db import async_session
from app.models import (
    ChatSession,
    CompanyProfile,
    KnowledgeDocument,
    Opportunity,
    OpportunityAnalysis,
    PipelineEntry,
)

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

        # Gather context using always-on search
        context = await gather_context(db, user_message)

        # Build system message with context
        system_msg = """You are an AI assistant for a government procurement opportunity tracking system.
You help users find and analyze government RFPs/RFQs, understand their pipeline, and make decisions about which opportunities to pursue.
You also have access to the company's knowledge base documents.

You have access to the following data context:
"""
        if context:
            system_msg += f"\n{context}\n"

        system_msg += """
When referencing specific opportunities, include their title and solicitation number if available.
Be concise and actionable in your responses. If asked about specific data, reference the context provided.
When you reference data from the knowledge base, mention the document title."""

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
    """Gather relevant database context using full-text search (always-on)."""
    context_parts = []

    # 1. Always load company profile
    company_ctx = await _load_company_context(db)
    if company_ctx:
        context_parts.append(company_ctx)

    # 2. Full-text search opportunities (always search — FTS is cheap)
    opp_ctx = await _search_opportunities_fts(db, user_message)
    if opp_ctx:
        context_parts.append(opp_ctx)

    # 3. Search knowledge base
    kb_ctx = await _search_knowledge_base(db, user_message)
    if kb_ctx:
        context_parts.append(kb_ctx)

    # 4. Pipeline status (always include summary)
    pipeline_ctx = await _get_pipeline_context(db)
    if pipeline_ctx:
        context_parts.append(pipeline_ctx)

    return "\n\n".join(context_parts)


async def _load_company_context(db) -> str:
    """Load company profile context."""
    result = await db.execute(select(CompanyProfile).limit(1))
    company = result.scalar_one_or_none()
    if not company:
        return ""

    parts = [f"COMPANY: {company.name}"]
    if company.description:
        parts.append(f"Description: {company.description[:500]}")
    if company.capabilities:
        caps = ", ".join(c.get("name", "") for c in company.capabilities[:10])
        parts.append(f"Capabilities: {caps}")
    if company.naics_codes:
        parts.append(f"NAICS: {', '.join(company.naics_codes[:10])}")
    return "\n".join(parts)


async def _search_opportunities_fts(db, user_message: str) -> str:
    """Search opportunities using full-text search."""
    try:
        ts_query = func.plainto_tsquery('english', user_message)
        query = (
            select(Opportunity)
            .options(joinedload(Opportunity.analysis))
            .where(Opportunity.search_vector.op('@@')(ts_query))
            .order_by(func.ts_rank(Opportunity.search_vector, ts_query).desc())
            .limit(8)
        )
        result = await db.execute(query)
        opps = result.unique().scalars().all()
    except Exception:
        # Fallback to ILIKE if FTS not available
        search_terms = [
            w for w in user_message.split()
            if len(w) > 3 and w.lower() not in {
                "what", "which", "show", "find", "about", "with", "that",
                "this", "from", "have", "opportunities", "opportunity",
                "should", "could", "would", "there", "their", "these",
            }
        ]
        if not search_terms:
            return ""
        conditions = []
        for term in search_terms[:3]:
            conditions.append(Opportunity.title.ilike(f"%{term}%"))
            conditions.append(Opportunity.description.ilike(f"%{term}%"))
            conditions.append(Opportunity.agency.ilike(f"%{term}%"))
        query = (
            select(Opportunity)
            .options(joinedload(Opportunity.analysis))
            .where(or_(*conditions))
            .order_by(desc(Opportunity.posted_date))
            .limit(8)
        )
        result = await db.execute(query)
        opps = result.unique().scalars().all()

    if not opps:
        return ""

    parts = [f"RELEVANT OPPORTUNITIES ({len(opps)} found):"]
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
        if opp.naics_code:
            line += f" | NAICS: {opp.naics_code}"
        parts.append(line)

    return "\n".join(parts)


async def _search_knowledge_base(db, user_message: str) -> str:
    """Search knowledge base using full-text search."""
    try:
        ts_query = func.plainto_tsquery('english', user_message)
        query = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.search_vector.op('@@')(ts_query))
            .order_by(func.ts_rank(KnowledgeDocument.search_vector, ts_query).desc())
            .limit(3)
        )
        result = await db.execute(query)
        docs = result.scalars().all()
    except Exception:
        return ""

    if not docs:
        return ""

    parts = ["KNOWLEDGE BASE CONTEXT:"]
    for doc in docs:
        text_preview = (doc.extracted_text or "")[:1500]
        parts.append(f"--- {doc.title} ({doc.category}) ---")
        parts.append(text_preview)

    return "\n".join(parts)


async def _get_pipeline_context(db) -> str:
    """Get pipeline summary context."""
    pipeline_result = await db.execute(
        select(PipelineEntry.stage, func.count(PipelineEntry.id))
        .group_by(PipelineEntry.stage)
    )
    counts = {row[0]: row[1] for row in pipeline_result.all()}
    if not counts:
        return ""

    parts = [f"PIPELINE STATUS: {json.dumps(counts)}"]

    # Recent pipeline entries
    recent = await db.execute(
        select(PipelineEntry)
        .options(joinedload(PipelineEntry.opportunity))
        .order_by(desc(PipelineEntry.updated_at))
        .limit(5)
    )
    entries = recent.unique().scalars().all()
    if entries:
        parts.append("Recent pipeline entries:")
        for e in entries:
            opp_title = e.opportunity.title if e.opportunity else "Unknown"
            parts.append(f"- {opp_title} | Stage: {e.stage} | Priority: {e.priority}")

    return "\n".join(parts)
