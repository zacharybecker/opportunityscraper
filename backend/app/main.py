import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, company, opportunities, scrapers, analysis, pipeline, chat, notifications, analytics, admin, codes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        from app.jobs import setup_scheduler, sync_scraper_schedules
        setup_scheduler()
        await sync_scraper_schedules()
        logger.info("Scheduler initialized")
    except Exception as e:
        logger.warning(f"Scheduler setup failed (non-fatal): {e}")
    yield
    # Shutdown
    try:
        from app.jobs import scheduler
        if scheduler:
            scheduler.shutdown(wait=False)
    except Exception:
        pass


app = FastAPI(title="OpportunityScraper API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all route modules under /api/v1
PREFIX = "/api/v1"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(company.router, prefix=PREFIX)
app.include_router(opportunities.router, prefix=PREFIX)
app.include_router(scrapers.router, prefix=PREFIX)
app.include_router(analysis.router, prefix=PREFIX)
app.include_router(pipeline.router, prefix=PREFIX)
app.include_router(chat.router, prefix=PREFIX)
app.include_router(notifications.router, prefix=PREFIX)
app.include_router(analytics.router, prefix=PREFIX)
app.include_router(admin.router, prefix=PREFIX)
app.include_router(codes.router, prefix=PREFIX)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
