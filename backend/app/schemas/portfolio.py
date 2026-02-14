from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PortfolioEntryCreate(BaseModel):
    listing_id: int
    status: str = "watching"
    purchase_price: Optional[float] = None
    notes: str = ""


class PortfolioEntryUpdate(BaseModel):
    status: Optional[str] = None
    purchase_price: Optional[float] = None
    actual_reno_cost: Optional[float] = None
    actual_sale_price: Optional[float] = None
    actual_weekly_rent: Optional[float] = None
    notes: Optional[str] = None


class PortfolioEntryResponse(BaseModel):
    id: int
    listing_id: int
    status: str
    purchase_price: Optional[float]
    actual_reno_cost: Optional[float]
    actual_sale_price: Optional[float]
    actual_weekly_rent: Optional[float]
    projected_reno_cost: Optional[float]
    projected_arv: Optional[float]
    projected_weekly_rent: Optional[float]
    projected_roi: Optional[float]
    notes: str
    created_at: datetime
    updated_at: datetime

    # Computed comparison fields
    reno_cost_variance: Optional[float] = None  # actual - projected
    roi_variance: Optional[float] = None

    class Config:
        from_attributes = True
