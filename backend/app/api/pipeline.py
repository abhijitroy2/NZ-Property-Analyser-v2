from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.services.pipeline import PropertyPipeline
from app.pipeline_status import set_idle, set_running, get_status

router = APIRouter()


@router.get("/status")
def pipeline_status() -> Dict[str, Any]:
    """Get current pipeline task status (for frontend display)."""
    return get_status()


@router.post("/run")
def run_pipeline(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Trigger the full processing pipeline (scrape + filter + analyze + score)."""
    background_tasks.add_task(_run_pipeline_task)
    return {"status": "started", "message": "Pipeline started in background"}


@router.post("/scrape")
def run_scrape_only(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Only run the TradeMe scraper (no analysis)."""
    background_tasks.add_task(_run_scrape_task)
    return {"status": "started", "message": "Scraper started in background"}


@router.post("/analyze")
def run_analyze_only(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Run analysis on all pending listings (skip scraping)."""
    background_tasks.add_task(_run_analysis_task)
    return {"status": "started", "message": "Analysis started in background"}


@router.post("/analyze/{listing_id}")
def analyze_single_listing(listing_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Run full analysis on a single listing."""
    from app.models.listing import Listing
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Listing not found")

    background_tasks.add_task(_run_single_analysis_task, listing_id)
    return {"status": "started", "message": f"Analysis started for listing {listing_id}"}


def _run_pipeline_task():
    """Background task: full pipeline."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        pipeline = PropertyPipeline(db)
        pipeline.run_full_pipeline()
    finally:
        db.close()


def _run_scrape_task():
    """Background task: scrape only."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        pipeline = PropertyPipeline(db)
        pipeline.scrape_new_listings()
    finally:
        db.close()
        set_idle()


def _run_analysis_task():
    """Background task: analyze pending listings."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        pipeline = PropertyPipeline(db)
        pipeline.analyze_pending_listings()
    finally:
        db.close()
        set_idle()


def _run_single_analysis_task(listing_id: int):
    """Background task: analyze a single listing."""
    from app.database import SessionLocal
    from app.models.listing import Listing
    db = SessionLocal()
    try:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        if listing:
            set_running("analyze", f"Analyzing: {listing.address or listing.listing_id}", {"current": 1, "total": 1})
            pipeline = PropertyPipeline(db)
            pipeline.analyze_listing(listing)
    finally:
        db.close()
        set_idle()
