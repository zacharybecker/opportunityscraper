import hashlib
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def scrape_generic_web(config: dict, since: Optional[datetime] = None) -> list[dict]:
    """Scrape opportunities from a web portal using CSS selectors."""
    base_url = config.get("base_url", "")
    search_url = config.get("search_url", "")
    selectors = config.get("selectors", {})
    pagination = config.get("pagination", {})
    date_format = config.get("date_format", "%m/%d/%Y")
    delay_ms = config.get("request_delay_ms", 1000)

    if not search_url or not selectors:
        raise ValueError("search_url and selectors are required for generic web scraper")

    listing_selector = selectors.get("listing_row", "tr")
    title_selector = selectors.get("title", "a")
    deadline_selector = selectors.get("deadline")
    detail_link_selector = selectors.get("detail_link", "a@href")
    description_selector = selectors.get("description")

    max_pages = pagination.get("max_pages", 10)
    page_param = pagination.get("param", "page")

    opportunities = []

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for page_num in range(1, max_pages + 1):
            url = search_url
            if pagination.get("type") == "page_param":
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}{page_param}={page_num}"

            try:
                response = await client.get(url)
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.select(listing_selector)

            if not rows:
                break

            for row in rows:
                try:
                    opp = extract_listing(
                        row, base_url, title_selector, deadline_selector,
                        detail_link_selector, date_format,
                    )
                    if opp:
                        opportunities.append(opp)
                except Exception as e:
                    logger.warning(f"Error extracting listing: {e}")

            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)

        # Fetch detail pages
        if description_selector:
            for opp in opportunities:
                if opp.get("source_url"):
                    try:
                        detail_resp = await client.get(opp["source_url"])
                        detail_resp.raise_for_status()
                        detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                        desc_el = detail_soup.select_one(description_selector)
                        if desc_el:
                            opp["description"] = desc_el.get_text(strip=True)
                        if delay_ms > 0:
                            await asyncio.sleep(delay_ms / 1000.0)
                    except Exception as e:
                        logger.warning(f"Error fetching detail {opp['source_url']}: {e}")

    logger.info(f"Generic web scraper found {len(opportunities)} opportunities")
    return opportunities


def extract_listing(
    row, base_url: str, title_sel: str, deadline_sel: str | None,
    link_sel: str, date_format: str,
) -> dict | None:
    """Extract an opportunity from a listing row."""
    # Title
    title_el = row.select_one(title_sel.split("@")[0]) if title_sel else None
    title = title_el.get_text(strip=True) if title_el else ""
    if not title:
        return None

    # Link
    link = None
    if "@" in link_sel:
        sel, attr = link_sel.rsplit("@", 1)
        link_el = row.select_one(sel)
        if link_el:
            link = link_el.get(attr, "")
    else:
        link_el = row.select_one(link_sel)
        if link_el:
            link = link_el.get("href", "")

    if link and not link.startswith("http"):
        link = urljoin(base_url, link)

    # Deadline
    deadline = None
    if deadline_sel:
        deadline_el = row.select_one(deadline_sel)
        if deadline_el:
            try:
                deadline = datetime.strptime(
                    deadline_el.get_text(strip=True), date_format
                ).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

    content_str = f"{title}{link or ''}"
    content_hash = hashlib.sha256(content_str.encode()).hexdigest()

    return {
        "external_id": content_hash[:16],
        "source": "generic_web",
        "source_url": link,
        "title": title,
        "solicitation_number": None,
        "description": None,
        "notice_type": None,
        "posted_date": datetime.now(timezone.utc),
        "response_deadline": deadline,
        "set_aside_type": None,
        "set_aside_description": None,
        "classification_code": None,
        "naics_code": None,
        "agency": None,
        "office": None,
        "place_of_performance_state": None,
        "place_of_performance_city": None,
        "contact_name": None,
        "contact_email": None,
        "contact_phone": None,
        "award_amount": None,
        "award_date": None,
        "awardee_name": None,
        "documents": [],
        "content_hash": content_hash,
        "raw_data": {"source_url": link, "title": title},
    }
