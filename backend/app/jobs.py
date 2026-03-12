import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.db import async_session
from app.models import (
    CompanyProfile,
    Opportunity,
    OpportunityAnalysis,
    ScraperConfig,
    ScrapeRun,
)
from app.scrapers import run_scraper

logger = logging.getLogger(__name__)

scheduler = None


def setup_scheduler():
    """Initialize APScheduler with PostgreSQL job store."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from app.config import settings

    # Use sync URL for APScheduler job store
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")

    jobstores = {
        "default": SQLAlchemyJobStore(url=sync_url),
    }

    global scheduler
    scheduler = AsyncIOScheduler(jobstores=jobstores)

    # Add fixed scheduled jobs
    scheduler.add_job(
        check_deadline_reminders,
        "cron",
        hour=8,
        minute=0,
        id="check_deadline_reminders",
        replace_existing=True,
    )
    scheduler.add_job(
        archive_expired_opportunities,
        "cron",
        hour=1,
        minute=0,
        id="archive_expired_opportunities",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("APScheduler started")
    return scheduler


async def seed_default_scrapers():
    """Create a default SAM.gov scraper if SAM_GOV_API_KEY is set and no scrapers exist."""
    from app.config import settings

    if not settings.SAM_GOV_API_KEY:
        logger.info("No SAM_GOV_API_KEY set, skipping default scraper seed")
        return

    async with async_session() as db:
        result = await db.execute(select(ScraperConfig))
        if result.scalars().first():
            logger.info("Scrapers already exist, skipping seed")
            return

        scraper = ScraperConfig(
            name="SAM.gov - All Opportunities",
            scraper_type="sam_gov",
            is_enabled=True,
            schedule_cron="0 6 * * *",  # Daily at 6 AM
            config={
                "api_key": settings.SAM_GOV_API_KEY,
                "lookback_days": 30,
            },
        )
        db.add(scraper)
        await db.commit()
        logger.info("Created default SAM.gov scraper with daily 6 AM schedule")

        # Trigger an initial run immediately
        run = ScrapeRun(
            scraper_config_id=scraper.id,
            status="pending",
            trigger_type="startup",
        )
        db.add(run)
        await db.commit()
        asyncio.create_task(execute_scrape_run(str(run.id)))
        logger.info("Triggered initial SAM.gov scrape run")


async def sync_scraper_schedules():
    """Sync scraper cron schedules to APScheduler."""
    global scheduler
    if not scheduler:
        return

    async with async_session() as db:
        result = await db.execute(select(ScraperConfig).where(ScraperConfig.is_enabled == True))
        configs = result.scalars().all()

        for config in configs:
            job_id = f"scraper_{config.id}"
            if config.schedule_cron:
                try:
                    from apscheduler.triggers.cron import CronTrigger
                    parts = config.schedule_cron.split()
                    if len(parts) == 5:
                        trigger = CronTrigger(
                            minute=parts[0],
                            hour=parts[1],
                            day=parts[2],
                            month=parts[3],
                            day_of_week=parts[4],
                        )
                        scheduler.add_job(
                            scheduled_scrape,
                            trigger,
                            args=[str(config.id)],
                            id=job_id,
                            replace_existing=True,
                        )
                        logger.info(f"Scheduled scraper {config.name} with cron: {config.schedule_cron}")
                except Exception as e:
                    logger.error(f"Failed to schedule scraper {config.name}: {e}")
            else:
                try:
                    scheduler.remove_job(job_id)
                except Exception:
                    pass


async def scheduled_scrape(scraper_config_id: str):
    """Execute a scheduled scrape run."""
    async with async_session() as db:
        result = await db.execute(
            select(ScraperConfig).where(ScraperConfig.id == scraper_config_id)
        )
        config = result.scalar_one_or_none()
        if not config or not config.is_enabled:
            return

        run = ScrapeRun(
            scraper_config_id=config.id,
            status="pending",
            trigger_type="scheduled",
        )
        db.add(run)
        await db.commit()

    await execute_scrape_run(str(run.id))


async def execute_scrape_run(run_id: str):
    """Execute a scrape run (called from routes or scheduler)."""
    async with async_session() as db:
        try:
            # Get run and config
            result = await db.execute(
                select(ScrapeRun).where(ScrapeRun.id == run_id)
            )
            run = result.scalar_one_or_none()
            if not run:
                return

            config_result = await db.execute(
                select(ScraperConfig).where(ScraperConfig.id == run.scraper_config_id)
            )
            config = config_result.scalar_one_or_none()
            if not config:
                return

            # Update status
            run.status = "running"
            run.started_at = datetime.now(timezone.utc)
            await db.commit()

            # Run scraper
            raw_opps = await run_scraper(
                config.scraper_type,
                config.config,
                config.last_run_at,
            )

            # Upsert opportunities
            new_count = 0
            updated_count = 0
            error_count = 0
            new_ids = []

            for opp_data in raw_opps:
                try:
                    existing = await db.execute(
                        select(Opportunity).where(
                            Opportunity.external_id == opp_data["external_id"],
                            Opportunity.source == opp_data["source"],
                        )
                    )
                    existing_opp = existing.scalar_one_or_none()

                    if existing_opp:
                        if existing_opp.content_hash != opp_data.get("content_hash"):
                            for key, value in opp_data.items():
                                if key not in ("raw_data",) and value is not None:
                                    setattr(existing_opp, key, value)
                            existing_opp.raw_data = opp_data.get("raw_data")
                            updated_count += 1
                    else:
                        new_opp = Opportunity(
                            scrape_run_id=run.id,
                            **{k: v for k, v in opp_data.items() if k != "raw_data"},
                            raw_data=opp_data.get("raw_data"),
                        )
                        db.add(new_opp)
                        await db.flush()
                        new_ids.append(str(new_opp.id))
                        new_count += 1
                except Exception as e:
                    logger.warning(f"Error upserting opportunity: {e}")
                    error_count += 1

            # Update run stats
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.stats = {
                "found": len(raw_opps),
                "new": new_count,
                "updated": updated_count,
                "errors": error_count,
            }

            # Update last_run_at on config
            config.last_run_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(
                f"Scrape run {run_id} completed: found={len(raw_opps)}, "
                f"new={new_count}, updated={updated_count}, errors={error_count}"
            )

            # Trigger analysis for new opportunities
            if new_ids:
                asyncio.create_task(analyze_new_opportunities(new_ids))

            # Check notifications
            from app.notifications import check_scrape_notifications
            asyncio.create_task(check_scrape_notifications(str(run.id)))

        except Exception as e:
            logger.error(f"Scrape run {run_id} failed: {e}")
            async with async_session() as err_db:
                result = await err_db.execute(
                    select(ScrapeRun).where(ScrapeRun.id == run_id)
                )
                run = result.scalar_one_or_none()
                if run:
                    run.status = "failed"
                    run.completed_at = datetime.now(timezone.utc)
                    run.error_message = str(e)
                    await err_db.commit()


async def analyze_new_opportunities(opportunity_ids: list[str]):
    """Analyze a batch of new opportunities."""
    from app.ai.analyzer import run_analysis_task

    for opp_id in opportunity_ids:
        try:
            await run_analysis_task(opp_id)
        except Exception as e:
            logger.error(f"Analysis task failed for {opp_id}: {e}")
        await asyncio.sleep(1)  # Rate limit between analyses


async def check_deadline_reminders():
    """Check for opportunities with approaching deadlines and send notifications."""
    async with async_session() as db:
        now = datetime.now(timezone.utc)
        upcoming = await db.execute(
            select(Opportunity).where(
                Opportunity.is_active == True,
                Opportunity.response_deadline.isnot(None),
                Opportunity.response_deadline >= now,
                Opportunity.response_deadline <= now + timedelta(days=3),
            )
        )
        opps = upcoming.scalars().all()

        if opps:
            from app.notifications import send_deadline_reminders
            await send_deadline_reminders(opps)

        logger.info(f"Deadline check: {len(opps)} approaching deadlines")


async def archive_expired_opportunities():
    """Mark expired opportunities as inactive."""
    async with async_session() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            update(Opportunity)
            .where(
                Opportunity.is_active == True,
                Opportunity.response_deadline.isnot(None),
                Opportunity.response_deadline < now - timedelta(days=1),
            )
            .values(is_active=False)
        )
        await db.commit()
        logger.info(f"Archived {result.rowcount} expired opportunities")
