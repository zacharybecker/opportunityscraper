from datetime import datetime
from typing import Optional

from .sam_gov import scrape_sam_gov
from .generic_web import scrape_generic_web

SCRAPERS = {
    "sam_gov": scrape_sam_gov,
    "generic_web": scrape_generic_web,
}


async def run_scraper(scraper_type: str, config: dict, since: Optional[datetime] = None) -> list[dict]:
    """Dispatch to the appropriate scraper and return normalized opportunity dicts."""
    scraper_fn = SCRAPERS.get(scraper_type)
    if not scraper_fn:
        raise ValueError(f"Unknown scraper type: {scraper_type}")
    return await scraper_fn(config, since)
