from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.watchlist import WatchlistItem
from app.schemas.watchlist import WatchlistItemCreate, WatchlistItemResponse, WatchlistItemUpdate

router = APIRouter()


@router.get("", response_model=List[WatchlistItemResponse])
def get_watchlist(db: Session = Depends(get_db)):
    """Get all saved searches / watchlist items."""
    items = db.query(WatchlistItem).order_by(WatchlistItem.created_at.desc()).all()
    return [WatchlistItemResponse.model_validate(item) for item in items]


@router.post("", response_model=WatchlistItemResponse)
def create_watchlist_item(item: WatchlistItemCreate, db: Session = Depends(get_db)):
    """Create a new saved search."""
    db_item = WatchlistItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return WatchlistItemResponse.model_validate(db_item)


@router.put("/{item_id}", response_model=WatchlistItemResponse)
def update_watchlist_item(item_id: int, update: WatchlistItemUpdate, db: Session = Depends(get_db)):
    """Update a saved search."""
    db_item = db.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return WatchlistItemResponse.model_validate(db_item)


@router.delete("/{item_id}")
def delete_watchlist_item(item_id: int, db: Session = Depends(get_db)):
    """Delete a saved search."""
    db_item = db.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    db.delete(db_item)
    db.commit()
    return {"detail": "Deleted"}
