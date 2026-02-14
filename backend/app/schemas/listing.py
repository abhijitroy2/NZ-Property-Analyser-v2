from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class ListingCreate(BaseModel):
    listing_id: str
    title: str = ""
    address: str = ""
    full_address: str = ""
    suburb: str = ""
    district: str = ""
    region: str = ""
    geographic_location: str = ""
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    land_area: Optional[float] = None
    floor_area: Optional[float] = None
    capital_value: str = ""
    property_type: str = ""
    title_type: str = ""
    display_price: str = ""
    asking_price: Optional[float] = None
    estimated_market_price: str = ""
    estimated_weekly_rent: str = ""
    description: str = ""
    property_url: str = ""
    photos: List[str] = []
    nearby_properties: List[Any] = []
    listing_date: Optional[datetime] = None
    source_url: str = ""


class ListingResponse(BaseModel):
    id: int
    listing_id: str
    title: str
    address: str
    full_address: str
    suburb: str
    district: str
    region: str
    geographic_location: str
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    land_area: Optional[float]
    floor_area: Optional[float]
    capital_value: str
    property_type: str
    title_type: str
    display_price: str
    asking_price: Optional[float]
    estimated_market_price: str
    estimated_weekly_rent: str
    description: str
    property_url: str
    photos: List[str]
    nearby_properties: List[Any]
    listing_date: Optional[datetime]
    filter_status: str
    filter_rejection_reason: str
    analysis_status: str
    created_at: datetime
    updated_at: datetime

    # Analysis summary (when joined)
    composite_score: Optional[float] = None
    verdict: Optional[str] = None
    recommended_strategy: Optional[str] = None

    class Config:
        from_attributes = True


class ListingListResponse(BaseModel):
    items: List[ListingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ListingFilters(BaseModel):
    strategy: Optional[str] = None  # FLIP, RENTAL, EITHER
    min_roi: Optional[float] = None
    max_timeline_weeks: Optional[int] = None
    regions: Optional[List[str]] = None
    suburbs: Optional[List[str]] = None
    min_score: Optional[float] = None
    max_price: Optional[float] = None
    min_bedrooms: Optional[int] = None
    verdict: Optional[str] = None  # STRONG_BUY, BUY, MAYBE, PASS
    filter_status: Optional[str] = None  # passed, rejected, pending
    sort_by: str = "composite_score"
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 20
