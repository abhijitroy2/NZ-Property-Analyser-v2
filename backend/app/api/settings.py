import os
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.models.search_url import SearchURL

logger = logging.getLogger(__name__)

router = APIRouter()

TM_SCRAPER_INPUT_PATH = r"C:\Users\OEM\TM-scraper-1\input.txt"


# --- Schemas ---

class SearchURLItem(BaseModel):
    id: Optional[int] = None
    url: str
    label: str = ""
    enabled: bool = True

    class Config:
        from_attributes = True


class SearchURLsResponse(BaseModel):
    urls: List[SearchURLItem]


class SearchURLsUpdate(BaseModel):
    urls: List[SearchURLItem]


# --- Endpoints ---

@router.get("/search-urls", response_model=SearchURLsResponse)
def get_search_urls(db: Session = Depends(get_db)):
    """Get all configured search URLs."""
    urls = db.query(SearchURL).order_by(SearchURL.id).all()
    return SearchURLsResponse(urls=[SearchURLItem.model_validate(u) for u in urls])


@router.put("/search-urls", response_model=SearchURLsResponse)
def update_search_urls(payload: SearchURLsUpdate, db: Session = Depends(get_db)):
    """
    Replace all search URLs with the provided list.
    Also syncs to the TM-scraper-1 input.txt file.
    """
    # Clear existing
    db.query(SearchURL).delete()
    db.flush()

    # Insert new
    new_urls = []
    for item in payload.urls:
        url_str = item.url.strip()
        if not url_str:
            continue
        db_url = SearchURL(
            url=url_str,
            label=item.label.strip(),
            enabled=item.enabled,
        )
        db.add(db_url)
        new_urls.append(db_url)

    db.commit()

    # Sync to TM-scraper input.txt
    _sync_to_scraper_input(new_urls)

    # Refresh to get IDs
    for u in new_urls:
        db.refresh(u)

    return SearchURLsResponse(urls=[SearchURLItem.model_validate(u) for u in new_urls])


@router.post("/search-urls/add", response_model=SearchURLItem)
def add_search_url(item: SearchURLItem, db: Session = Depends(get_db)):
    """Add a single search URL."""
    db_url = SearchURL(
        url=item.url.strip(),
        label=item.label.strip(),
        enabled=item.enabled,
    )
    db.add(db_url)
    db.commit()
    db.refresh(db_url)

    # Sync all enabled URLs to TM-scraper input.txt
    all_urls = db.query(SearchURL).filter(SearchURL.enabled == True).all()
    _sync_to_scraper_input(all_urls)

    return SearchURLItem.model_validate(db_url)


@router.delete("/search-urls/{url_id}")
def delete_search_url(url_id: int, db: Session = Depends(get_db)):
    """Delete a search URL by ID."""
    url = db.query(SearchURL).filter(SearchURL.id == url_id).first()
    if not url:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Search URL not found")

    db.delete(url)
    db.commit()

    # Sync remaining enabled URLs
    remaining = db.query(SearchURL).filter(SearchURL.enabled == True).all()
    _sync_to_scraper_input(remaining)

    return {"status": "deleted", "id": url_id}


@router.patch("/search-urls/{url_id}/toggle")
def toggle_search_url(url_id: int, db: Session = Depends(get_db)):
    """Toggle a search URL enabled/disabled."""
    url = db.query(SearchURL).filter(SearchURL.id == url_id).first()
    if not url:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Search URL not found")

    url.enabled = not url.enabled
    db.commit()

    # Sync enabled URLs
    all_urls = db.query(SearchURL).filter(SearchURL.enabled == True).all()
    _sync_to_scraper_input(all_urls)

    return {"status": "toggled", "id": url_id, "enabled": url.enabled}


# --- Helpers ---

def _sync_to_scraper_input(urls: List[SearchURL]):
    """Write enabled URLs to the TM-scraper-1 input.txt file."""
    enabled_urls = [u.url for u in urls if u.enabled]
    try:
        os.makedirs(os.path.dirname(TM_SCRAPER_INPUT_PATH), exist_ok=True)
        with open(TM_SCRAPER_INPUT_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(enabled_urls))
        logger.info(f"Synced {len(enabled_urls)} URLs to {TM_SCRAPER_INPUT_PATH}")
    except Exception as e:
        logger.error(f"Failed to sync URLs to {TM_SCRAPER_INPUT_PATH}: {e}")


def get_active_search_urls(db: Session) -> List[str]:
    """
    Get the list of active search URLs.
    Falls back to .env TRADEME_SEARCH_URLS if no DB entries exist.
    """
    urls = db.query(SearchURL).filter(SearchURL.enabled == True).all()
    if urls:
        return [u.url for u in urls]

    # Fallback to .env
    from app.config import settings
    return settings.search_urls
