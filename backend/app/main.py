import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api import listings, analysis, dashboard, watchlist, portfolio, pipeline
from app.api.settings import router as settings_router

# Configure logging so all loggers output to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logging.getLogger("app").setLevel(logging.DEBUG)

app = FastAPI(
    title="NZ Property Finder",
    description="NZ Property Investment Evaluation System - Automated property scanning, analysis, and scoring",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(listings.router, prefix="/api/listings", tags=["Listings"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["Watchlist"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["Pipeline"])
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])


@app.on_event("startup")
async def startup_event():
    """Initialize database, seed search URLs if empty, optionally start scheduler."""
    init_db()
    _seed_search_urls()

    if settings.enable_scheduler:
        from app.tasks.scheduler import start_scheduler
        start_scheduler()


def _seed_search_urls():
    """If no search URLs in DB yet, seed from .env config."""
    from app.database import SessionLocal
    from app.models.search_url import SearchURL
    db = SessionLocal()
    try:
        count = db.query(SearchURL).count()
        if count == 0 and settings.trademe_search_urls:
            for url in settings.search_urls:
                db.add(SearchURL(url=url, label="", enabled=True))
            db.commit()
            logging.getLogger(__name__).info(f"Seeded {len(settings.search_urls)} search URLs from .env")
    finally:
        db.close()


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
