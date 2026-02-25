import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_role
from app.db import get_db
from app.models import ScraperConfig, ScrapeRun, User
from app.schemas import (
    ScraperConfigCreate,
    ScraperConfigResponse,
    ScraperConfigUpdate,
    ScrapeRunResponse,
)

router = APIRouter(prefix="/scrapers", tags=["scrapers"])


@router.get("", response_model=list[ScraperConfigResponse])
async def list_scrapers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(ScraperConfig).order_by(ScraperConfig.created_at))
    return [ScraperConfigResponse.model_validate(s) for s in result.scalars().all()]


@router.post("", response_model=ScraperConfigResponse)
async def create_scraper(
    body: ScraperConfigCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    scraper = ScraperConfig(**body.model_dump())
    db.add(scraper)
    await db.flush()
    return ScraperConfigResponse.model_validate(scraper)


@router.put("/{scraper_id}", response_model=ScraperConfigResponse)
async def update_scraper(
    scraper_id: str,
    body: ScraperConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    result = await db.execute(select(ScraperConfig).where(ScraperConfig.id == scraper_id))
    scraper = result.scalar_one_or_none()
    if not scraper:
        raise HTTPException(status_code=404, detail="Scraper not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(scraper, key, value)
    await db.flush()
    return ScraperConfigResponse.model_validate(scraper)


@router.delete("/{scraper_id}")
async def delete_scraper(
    scraper_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    result = await db.execute(select(ScraperConfig).where(ScraperConfig.id == scraper_id))
    scraper = result.scalar_one_or_none()
    if not scraper:
        raise HTTPException(status_code=404, detail="Scraper not found")

    await db.delete(scraper)
    return {"status": "deleted"}


@router.post("/{scraper_id}/run", response_model=ScrapeRunResponse)
async def trigger_run(
    scraper_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("analyst")),
):
    result = await db.execute(select(ScraperConfig).where(ScraperConfig.id == scraper_id))
    scraper = result.scalar_one_or_none()
    if not scraper:
        raise HTTPException(status_code=404, detail="Scraper not found")

    run = ScrapeRun(
        scraper_config_id=scraper.id,
        status="pending",
        trigger_type="manual",
    )
    db.add(run)
    await db.flush()

    # Launch background scrape
    from app.jobs import execute_scrape_run
    asyncio.create_task(execute_scrape_run(str(run.id)))

    return ScrapeRunResponse.model_validate(run)


@router.get("/{scraper_id}/runs", response_model=list[ScrapeRunResponse])
async def list_runs(
    scraper_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScrapeRun)
        .where(ScrapeRun.scraper_config_id == scraper_id)
        .order_by(desc(ScrapeRun.created_at))
        .limit(50)
    )
    return [ScrapeRunResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/run-all")
async def run_all_scrapers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("analyst")),
):
    result = await db.execute(
        select(ScraperConfig).where(ScraperConfig.is_enabled == True)
    )
    scrapers = result.scalars().all()

    runs = []
    for scraper in scrapers:
        run = ScrapeRun(
            scraper_config_id=scraper.id,
            status="pending",
            trigger_type="manual",
        )
        db.add(run)
        runs.append(run)
    await db.flush()

    from app.jobs import execute_scrape_run
    for run in runs:
        asyncio.create_task(execute_scrape_run(str(run.id)))

    return {"status": "queued", "count": len(runs)}
