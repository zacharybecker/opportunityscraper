import json
import logging

from app.ai.client import chat_completion

logger = logging.getLogger(__name__)


async def extract_opportunity_from_text(text: str) -> dict:
    """Use AI to extract structured opportunity fields from unstructured text."""
    result = await chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are an expert at extracting structured data from government procurement documents. Return ONLY valid JSON.",
            },
            {
                "role": "user",
                "content": f"""Extract opportunity details from this text. Return JSON with these fields (use null for missing):
{{
    "title": "opportunity title",
    "description": "full description",
    "agency": "issuing agency",
    "solicitation_number": "solicitation/RFP number",
    "naics_code": "NAICS code (6 digits)",
    "set_aside_type": "small business set-aside type if any",
    "response_deadline": "deadline in ISO format or null",
    "contact_name": "point of contact name",
    "contact_email": "contact email",
    "contact_phone": "contact phone",
    "place_of_performance_state": "2-letter state code",
    "place_of_performance_city": "city name",
    "notice_type": "type (presolicitation/combined/solicitation/sources_sought/etc)"
}}

TEXT:
{text[:8000]}""",
            },
        ],
        response_format={"type": "json_object"},
    )

    try:
        extracted = json.loads(result["content"])
        return extracted
    except json.JSONDecodeError:
        logger.error("Failed to parse AI extraction response")
        return {}
