import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

SAM_API_BASE = "https://api.sam.gov/opportunities/v2/search"


async def scrape_sam_gov(config: dict, since: Optional[datetime] = None) -> list[dict]:
    """Scrape opportunities from SAM.gov API."""
    api_key = config.get("api_key", "")
    if not api_key:
        raise ValueError("SAM.gov API key is required")

    lookback_days = config.get("lookback_days", 30)
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    params = {
        "api_key": api_key,
        "postedFrom": since.strftime("%m/%d/%Y"),
        "postedTo": datetime.now(timezone.utc).strftime("%m/%d/%Y"),
        "limit": 100,
        "offset": 0,
    }

    # Add optional filters
    if config.get("naics_codes"):
        params["naics"] = ",".join(config["naics_codes"])
    if config.get("psc_codes"):
        params["psc"] = ",".join(config["psc_codes"])
    if config.get("notice_types"):
        params["ntype"] = ",".join(config["notice_types"])
    if config.get("set_aside_types"):
        params["typeOfSetAside"] = ",".join(config["set_aside_types"])
    if config.get("states"):
        params["state"] = ",".join(config["states"])
    if config.get("keywords"):
        params["keyword"] = " ".join(config["keywords"])

    opportunities = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            try:
                response = await client.get(SAM_API_BASE, params=params)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"SAM.gov API error: {e.response.status_code} - {e.response.text}")
                break
            except Exception as e:
                logger.error(f"SAM.gov request error: {e}")
                break

            opps_data = data.get("opportunitiesData", [])
            if not opps_data:
                break

            for opp in opps_data:
                normalized = normalize_sam_opportunity(opp)
                opportunities.append(normalized)

            # Check if there are more pages
            total = data.get("totalRecords", 0)
            params["offset"] += len(opps_data)
            if params["offset"] >= total:
                break

    logger.info(f"SAM.gov scraper found {len(opportunities)} opportunities")
    return opportunities


def normalize_sam_opportunity(opp: dict) -> dict:
    """Normalize a SAM.gov opportunity to our standard format."""
    # Build content hash for dedup
    content_str = f"{opp.get('noticeId', '')}{opp.get('title', '')}{opp.get('description', '')}"
    content_hash = hashlib.sha256(content_str.encode()).hexdigest()

    # Parse dates
    posted = parse_sam_date(opp.get("postedDate"))
    deadline = parse_sam_date(opp.get("responseDeadLine") or opp.get("archiveDate"))

    # Extract documents
    documents = []
    for link in opp.get("resourceLinks", []):
        if isinstance(link, str):
            documents.append({
                "filename": link.split("/")[-1] if "/" in link else link,
                "url": link,
                "parsed_text": None,
                "parse_status": "pending",
            })

    # Extract contact
    poc = opp.get("pointOfContact", [{}])
    primary_poc = poc[0] if poc else {}

    # Extract place of performance
    pop = opp.get("placeOfPerformance", {})
    state_code = None
    city = None
    if isinstance(pop, dict):
        state_info = pop.get("state", {})
        if isinstance(state_info, dict):
            state_code = state_info.get("code")
        city_info = pop.get("city", {})
        if isinstance(city_info, dict):
            city = city_info.get("name")

    return {
        "external_id": opp.get("noticeId", ""),
        "source": "sam_gov",
        "source_url": f"https://sam.gov/opp/{opp.get('noticeId', '')}",
        "title": opp.get("title", "Untitled"),
        "solicitation_number": opp.get("solicitationNumber"),
        "description": opp.get("description", ""),
        "notice_type": opp.get("type"),
        "posted_date": posted,
        "response_deadline": deadline,
        "set_aside_type": opp.get("typeOfSetAsideDescription") or opp.get("typeOfSetAside"),
        "set_aside_description": opp.get("typeOfSetAsideDescription"),
        "classification_code": opp.get("classificationCode"),
        "naics_code": opp.get("naicsCode"),
        "agency": opp.get("fullParentPathName") or opp.get("department"),
        "office": opp.get("officeAddress", {}).get("name") if isinstance(opp.get("officeAddress"), dict) else None,
        "place_of_performance_state": state_code,
        "place_of_performance_city": city,
        "contact_name": primary_poc.get("fullName"),
        "contact_email": primary_poc.get("email"),
        "contact_phone": primary_poc.get("phone"),
        "award_amount": parse_float(opp.get("award", {}).get("amount") if isinstance(opp.get("award"), dict) else None),
        "award_date": opp.get("award", {}).get("date") if isinstance(opp.get("award"), dict) else None,
        "awardee_name": opp.get("award", {}).get("awardee", {}).get("name") if isinstance(opp.get("award"), dict) else None,
        "documents": documents,
        "content_hash": content_hash,
        "raw_data": opp,
    }


def parse_sam_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def parse_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
