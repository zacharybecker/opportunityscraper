import logging

from app.ai.client import chat_completion

logger = logging.getLogger(__name__)


async def generate_section(
    section_title: str,
    section_desc: str,
    opportunity_context: str,
    company_context: str,
    template_hints: str = "",
) -> str:
    """Generate a proposal section using AI."""
    result = await chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are an expert government proposal writer. Write compelling, professional proposal sections that directly address requirements.",
            },
            {
                "role": "user",
                "content": f"""Write the "{section_title}" section for a government proposal.

Section description: {section_desc}
{f"Template guidance: {template_hints}" if template_hints else ""}

COMPANY CONTEXT:
{company_context}

OPPORTUNITY:
{opportunity_context}

Write a professional, detailed section (500-1000 words) that:
1. Directly addresses the opportunity requirements
2. Highlights relevant company capabilities and past performance
3. Uses specific, quantifiable examples where possible
4. Maintains a confident, professional tone""",
            },
        ],
        max_tokens=2000,
    )
    return result["content"]


async def rewrite_text(text: str, instruction: str, context: str = "") -> str:
    """Rewrite text according to instructions."""
    result = await chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are an expert editor for government proposals. Rewrite the provided text following the instructions.",
            },
            {
                "role": "user",
                "content": f"""Rewrite the following text.

Instructions: {instruction}
{f"Context: {context}" if context else ""}

TEXT TO REWRITE:
{text}

Return only the rewritten text, no explanations.""",
            },
        ],
        max_tokens=2000,
    )
    return result["content"]


async def expand_text(text: str, context: str = "") -> str:
    """Expand text with more detail."""
    result = await chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are an expert government proposal writer. Expand the provided text with more detail, examples, and supporting information.",
            },
            {
                "role": "user",
                "content": f"""Expand the following text with more detail, specific examples, and supporting information.
{f"Context: {context}" if context else ""}

TEXT TO EXPAND:
{text}

Return only the expanded text.""",
            },
        ],
        max_tokens=2000,
    )
    return result["content"]


async def add_compliance_language(text: str, opportunity_context: str) -> str:
    """Add compliance language to text."""
    result = await chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are an expert in government contracting compliance. Add relevant compliance language to the provided text.",
            },
            {
                "role": "user",
                "content": f"""Add relevant compliance language to this proposal text based on the opportunity requirements.

OPPORTUNITY CONTEXT:
{opportunity_context}

TEXT:
{text}

Add appropriate regulatory compliance references, certifications, and standards language. Return only the enhanced text.""",
            },
        ],
        max_tokens=2000,
    )
    return result["content"]
