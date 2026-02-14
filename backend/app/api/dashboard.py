from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

from app.database import get_db
from app.models.listing import Listing
from app.models.analysis import Analysis

router = APIRouter()


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get dashboard summary statistics."""
    total_listings = db.query(func.count(Listing.id)).scalar() or 0
    passed_filters = db.query(func.count(Listing.id)).filter(Listing.filter_status == "passed").scalar() or 0
    rejected = db.query(func.count(Listing.id)).filter(Listing.filter_status == "rejected").scalar() or 0
    pending = db.query(func.count(Listing.id)).filter(Listing.filter_status == "pending").scalar() or 0
    analyzed = db.query(func.count(Listing.id)).filter(Listing.analysis_status == "completed").scalar() or 0

    # Verdict breakdown
    verdict_counts = (
        db.query(Analysis.verdict, func.count(Analysis.id))
        .filter(Analysis.verdict != "")
        .group_by(Analysis.verdict)
        .all()
    )
    verdicts = {v[0]: v[1] for v in verdict_counts}

    # Average score
    avg_score = db.query(func.avg(Analysis.composite_score)).filter(Analysis.composite_score.isnot(None)).scalar()

    return {
        "total_listings": total_listings,
        "passed_filters": passed_filters,
        "rejected": rejected,
        "pending": pending,
        "analyzed": analyzed,
        "verdicts": verdicts,
        "average_score": round(avg_score, 1) if avg_score else 0,
    }


@router.get("/top-deals")
def get_top_deals(limit: int = 5, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get top N deals by composite score."""
    results = (
        db.query(Listing, Analysis)
        .join(Analysis)
        .filter(Analysis.composite_score.isnot(None))
        .filter(Analysis.verdict.in_(["STRONG_BUY", "BUY"]))
        .order_by(Analysis.composite_score.desc())
        .limit(limit)
        .all()
    )

    deals = []
    for listing, analysis in results:
        strategy = analysis.strategy_decision or {}
        flip = analysis.flip_financials or {}
        rental = analysis.rental_financials or {}

        deals.append({
            "id": listing.id,
            "listing_id": listing.listing_id,
            "address": listing.full_address or listing.address,
            "suburb": listing.suburb,
            "region": listing.region,
            "display_price": listing.display_price,
            "asking_price": listing.asking_price,
            "bedrooms": listing.bedrooms,
            "bathrooms": listing.bathrooms,
            "composite_score": analysis.composite_score,
            "verdict": analysis.verdict,
            "recommended_strategy": strategy.get("recommended_strategy", ""),
            "flip_roi": flip.get("roi_percentage", 0),
            "rental_yield": rental.get("gross_yield_percentage", 0),
            "timeline_weeks": (analysis.timeline_estimate or {}).get("estimated_weeks", 0),
            "property_url": listing.property_url,
        })

    return deals


@router.get("/stats-by-region")
def get_stats_by_region(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get aggregate stats grouped by region."""
    results = (
        db.query(
            Listing.region,
            func.count(Listing.id).label("total"),
            func.avg(Listing.asking_price).label("avg_price"),
            func.avg(Analysis.composite_score).label("avg_score"),
        )
        .outerjoin(Analysis)
        .filter(Listing.region != "")
        .group_by(Listing.region)
        .order_by(func.count(Listing.id).desc())
        .all()
    )

    return [
        {
            "region": r.region,
            "total_listings": r.total,
            "avg_price": round(r.avg_price, 0) if r.avg_price else 0,
            "avg_score": round(r.avg_score, 1) if r.avg_score else 0,
        }
        for r in results
    ]
