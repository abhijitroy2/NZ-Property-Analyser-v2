from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class WatchlistItemCreate(BaseModel):
    name: str
    search_criteria: Dict[str, Any] = {}
    alert_enabled: bool = True


class WatchlistItemUpdate(BaseModel):
    name: Optional[str] = None
    search_criteria: Optional[Dict[str, Any]] = None
    alert_enabled: Optional[bool] = None


class WatchlistItemResponse(BaseModel):
    id: int
    name: str
    search_criteria: Dict[str, Any]
    alert_enabled: bool
    last_alerted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    matching_count: Optional[int] = None  # Number of listings matching criteria

    class Config:
        from_attributes = True
