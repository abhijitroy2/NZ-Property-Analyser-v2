from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models.listing import Listing
from app.models.analysis import Analysis
from app.schemas.listing import ListingResponse, ListingListResponse

router = APIRouter()


@router.get("", response_model=ListingListResponse)
def get_listings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    filter_status: Optional[str] = None,
    verdict: Optional[str] = None,
    region: Optional[str] = None,
    min_score: Optional[float] = None,
    max_price: Optional[float] = None,
    min_bedrooms: Optional[int] = None,
    sort_by: str = "composite_score",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
):
    """Get paginated, filtered list of property listings."""
    query = db.query(Listing)

    # Apply filters
    if filter_status:
        query = query.filter(Listing.filter_status == filter_status)
    if max_price:
        query = query.filter(Listing.asking_price <= max_price)
    if min_bedrooms:
        query = query.filter(Listing.bedrooms >= min_bedrooms)
    if region:
        query = query.filter(Listing.region == region)

    # Join with analysis for score/verdict filters
    if verdict or min_score or sort_by == "composite_score":
        query = query.outerjoin(Analysis)
        if verdict:
            query = query.filter(Analysis.verdict == verdict)
        if min_score:
            query = query.filter(Analysis.composite_score >= min_score)

    # Count total
    total = query.count()

    # Sorting
    if sort_by == "composite_score":
        order_col = Analysis.composite_score if sort_order == "desc" else Analysis.composite_score
        query = query.outerjoin(Analysis) if not (verdict or min_score) else query
        query = query.order_by(Analysis.composite_score.desc() if sort_order == "desc" else Analysis.composite_score.asc())
    elif sort_by == "asking_price":
        query = query.order_by(Listing.asking_price.desc() if sort_order == "desc" else Listing.asking_price.asc())
    elif sort_by == "listing_date":
        query = query.order_by(Listing.listing_date.desc() if sort_order == "desc" else Listing.listing_date.asc())
    elif sort_by == "created_at":
        query = query.order_by(Listing.created_at.desc() if sort_order == "desc" else Listing.created_at.asc())
    else:
        query = query.order_by(Listing.created_at.desc())

    # Paginate
    offset = (page - 1) * page_size
    listings = query.offset(offset).limit(page_size).all()

    # Build response with analysis summary
    items = []
    for listing in listings:
        data = ListingResponse.model_validate(listing)
        if listing.analysis:
            data.composite_score = listing.analysis.composite_score
            data.verdict = listing.analysis.verdict
            if listing.analysis.strategy_decision:
                data.recommended_strategy = listing.analysis.strategy_decision.get("recommended_strategy", "")
        items.append(data)

    total_pages = (total + page_size - 1) // page_size

    return ListingListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    """Get a single listing by ID."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Listing not found")

    data = ListingResponse.model_validate(listing)
    if listing.analysis:
        data.composite_score = listing.analysis.composite_score
        data.verdict = listing.analysis.verdict
        if listing.analysis.strategy_decision:
            data.recommended_strategy = listing.analysis.strategy_decision.get("recommended_strategy", "")
    return data


@router.get("/regions/list")
def get_regions(db: Session = Depends(get_db)):
    """Get list of all regions with listing counts."""
    from sqlalchemy import func
    results = (
        db.query(Listing.region, func.count(Listing.id))
        .filter(Listing.region != "")
        .group_by(Listing.region)
        .order_by(func.count(Listing.id).desc())
        .all()
    )
    return [{"region": r[0], "count": r[1]} for r in results]
