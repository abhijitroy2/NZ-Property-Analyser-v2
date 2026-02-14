from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class AnalysisResponse(BaseModel):
    id: int
    listing_id: int

    # Stage 1
    population_data: Optional[Dict[str, Any]] = None
    demand_profile: Optional[Dict[str, Any]] = None

    # Stage 2
    insurability: Optional[Dict[str, Any]] = None
    image_analysis: Optional[Dict[str, Any]] = None
    renovation_estimate: Optional[Dict[str, Any]] = None
    timeline_estimate: Optional[Dict[str, Any]] = None
    arv_estimate: Optional[Dict[str, Any]] = None
    rental_estimate: Optional[Dict[str, Any]] = None
    council_rates: Optional[Dict[str, Any]] = None
    subdivision_analysis: Optional[Dict[str, Any]] = None

    # Stage 3
    flip_financials: Optional[Dict[str, Any]] = None
    rental_financials: Optional[Dict[str, Any]] = None
    strategy_decision: Optional[Dict[str, Any]] = None

    # Scoring
    composite_score: Optional[float] = None
    component_scores: Optional[Dict[str, float]] = None
    verdict: str = ""
    rank: Optional[int] = None

    # Flags
    flags: List[str] = []
    next_steps: List[str] = []
    confidence_level: str = ""

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScenarioRequest(BaseModel):
    """Request to recalculate financials with custom inputs (interactive sliders)."""
    purchase_price: Optional[float] = None
    renovation_budget: Optional[float] = None
    sale_price: Optional[float] = None  # For flip scenario
    weekly_rent: Optional[float] = None  # For rental scenario
    interest_rate: Optional[float] = None
    timeline_weeks: Optional[int] = None


class ScenarioResponse(BaseModel):
    flip_financials: Dict[str, Any]
    rental_financials: Dict[str, Any]
    strategy_decision: Dict[str, Any]


class PropertyReport(BaseModel):
    """Full property report as specified in the algorithm doc section 6.1."""
    listing_id: str
    address: str
    listing_url: str

    # Verdict
    overall_verdict: str
    composite_score: float
    rank: Optional[int] = None

    # Strategy
    recommended_strategy: Dict[str, Any]

    # Financial summaries
    flip_scenario: Dict[str, Any]
    rental_scenario: Dict[str, Any]

    # Property details
    property: Dict[str, Any]

    # Analysis details
    renovation: Dict[str, Any]
    location: Dict[str, Any]
    insurability: Dict[str, Any]
    subdivision: Dict[str, Any]

    # Comparables
    comparable_sales: List[Any]
    rental_comps: List[Any]

    # Flags and next steps
    flags: List[str]
    confidence_level: str
    next_steps: List[str]
