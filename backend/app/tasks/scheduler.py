"""
Scheduled Task Runner.
Uses APScheduler for daily batch processing of property listings.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def start_scheduler():
    """Start the background scheduler for daily pipeline runs."""
    logger.info(
        f"Starting scheduler: daily at {settings.scheduler_hour:02d}:{settings.scheduler_minute:02d}"
    )

    scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(
            hour=settings.scheduler_hour,
            minute=settings.scheduler_minute,
        ),
        id="daily_pipeline",
        name="Daily Property Pipeline",
        replace_existing=True,
    )

    scheduler.add_job(
        check_watchlist_alerts,
        trigger=CronTrigger(
            hour=settings.scheduler_hour,
            minute=settings.scheduler_minute + 30,  # 30 min after pipeline
        ),
        id="watchlist_alerts",
        name="Watchlist Alert Check",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    """Stop the scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")


def run_daily_pipeline():
    """Daily pipeline job: scrape, filter, analyze, score, notify."""
    from app.database import SessionLocal
    from app.services.pipeline import PropertyPipeline
    from app.services.notifications.email_service import send_daily_digest

    logger.info("=== Daily pipeline job started ===")

    db = SessionLocal()
    try:
        # Run full pipeline
        pipeline = PropertyPipeline(db)
        pipeline.run_full_pipeline()

        # Send email digest if configured
        if settings.email_to:
            send_daily_digest(db)

    except Exception as e:
        logger.error(f"Daily pipeline failed: {e}")
    finally:
        db.close()

    logger.info("=== Daily pipeline job complete ===")


def check_watchlist_alerts():
    """Check watchlist items for matching new listings and send alerts."""
    from app.database import SessionLocal
    from app.models.watchlist import WatchlistItem
    from app.models.listing import Listing
    from app.models.analysis import Analysis
    from app.services.notifications.email_service import send_watchlist_alert
    from datetime import datetime, timezone, timedelta

    logger.info("Checking watchlist alerts")

    db = SessionLocal()
    try:
        watchlist_items = db.query(WatchlistItem).filter(WatchlistItem.alert_enabled == True).all()

        for item in watchlist_items:
            criteria = item.search_criteria or {}
            # Find new matching listings since last alert
            since = item.last_alerted_at or (datetime.now(timezone.utc) - timedelta(days=1))

            query = db.query(Listing).filter(
                Listing.created_at > since,
                Listing.filter_status == "passed",
            )

            # Apply saved criteria
            if criteria.get("max_price"):
                query = query.filter(Listing.asking_price <= criteria["max_price"])
            if criteria.get("min_bedrooms"):
                query = query.filter(Listing.bedrooms >= criteria["min_bedrooms"])
            if criteria.get("regions"):
                query = query.filter(Listing.region.in_(criteria["regions"]))
            if criteria.get("min_score"):
                query = query.join(Analysis).filter(
                    Analysis.composite_score >= criteria["min_score"]
                )

            matches = query.all()

            if matches and settings.email_to:
                send_watchlist_alert(item.name, matches)
                item.last_alerted_at = datetime.now(timezone.utc)

        db.commit()
    except Exception as e:
        logger.error(f"Watchlist alert check failed: {e}")
    finally:
        db.close()
