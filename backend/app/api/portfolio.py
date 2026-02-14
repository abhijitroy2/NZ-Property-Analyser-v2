from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.portfolio import PortfolioEntry
from app.models.listing import Listing
from app.models.analysis import Analysis
from app.schemas.portfolio import PortfolioEntryCreate, PortfolioEntryResponse, PortfolioEntryUpdate

router = APIRouter()


@router.get("", response_model=List[PortfolioEntryResponse])
def get_portfolio(db: Session = Depends(get_db)):
    """Get all portfolio entries."""
    entries = db.query(PortfolioEntry).order_by(PortfolioEntry.updated_at.desc()).all()
    result = []
    for entry in entries:
        resp = PortfolioEntryResponse.model_validate(entry)
        # Calculate variances
        if entry.actual_reno_cost and entry.projected_reno_cost:
            resp.reno_cost_variance = entry.actual_reno_cost - entry.projected_reno_cost
        result.append(resp)
    return result


@router.post("", response_model=PortfolioEntryResponse)
def create_portfolio_entry(entry: PortfolioEntryCreate, db: Session = Depends(get_db)):
    """Add a listing to portfolio tracking."""
    listing = db.query(Listing).filter(Listing.id == entry.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Check if already in portfolio
    existing = db.query(PortfolioEntry).filter(PortfolioEntry.listing_id == entry.listing_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Listing already in portfolio")

    # Pre-fill projected values from analysis
    analysis = db.query(Analysis).filter(Analysis.listing_id == entry.listing_id).first()

    db_entry = PortfolioEntry(**entry.model_dump())
    if analysis:
        reno = analysis.renovation_estimate or {}
        arv = analysis.arv_estimate or {}
        rental = analysis.rental_estimate or {}
        flip = analysis.flip_financials or {}
        db_entry.projected_reno_cost = reno.get("total_estimated")
        db_entry.projected_arv = arv.get("estimated_arv")
        db_entry.projected_weekly_rent = rental.get("estimated_weekly_rent")
        db_entry.projected_roi = flip.get("roi_percentage")

    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return PortfolioEntryResponse.model_validate(db_entry)


@router.put("/{entry_id}", response_model=PortfolioEntryResponse)
def update_portfolio_entry(entry_id: int, update: PortfolioEntryUpdate, db: Session = Depends(get_db)):
    """Update a portfolio entry with actual results."""
    db_entry = db.query(PortfolioEntry).filter(PortfolioEntry.id == entry_id).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Portfolio entry not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_entry, key, value)

    db.commit()
    db.refresh(db_entry)
    return PortfolioEntryResponse.model_validate(db_entry)


@router.delete("/{entry_id}")
def delete_portfolio_entry(entry_id: int, db: Session = Depends(get_db)):
    """Remove a portfolio entry."""
    db_entry = db.query(PortfolioEntry).filter(PortfolioEntry.id == entry_id).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Portfolio entry not found")

    db.delete(db_entry)
    db.commit()
    return {"detail": "Deleted"}
