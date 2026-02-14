from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api import listings, analysis, dashboard, watchlist, portfolio, pipeline

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


@app.on_event("startup")
async def startup_event():
    """Initialize database and optionally start scheduler."""
    init_db()

    if settings.enable_scheduler:
        from app.tasks.scheduler import start_scheduler
        start_scheduler()


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
