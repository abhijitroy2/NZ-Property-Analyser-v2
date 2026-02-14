from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.listing import Listing
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisResponse, ScenarioRequest, ScenarioResponse, PropertyReport
from app.services.financial.flip_model import calculate_flip_financials
from app.services.financial.rental_model import calculate_rental_financials
from app.services.financial.strategy import decide_strategy

router = APIRouter()


@router.get("/{listing_id}", response_model=AnalysisResponse)
def get_analysis(listing_id: int, db: Session = Depends(get_db)):
    """Get full analysis for a listing."""
    analysis = db.query(Analysis).filter(Analysis.listing_id == listing_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found for this listing")
    return analysis


@router.post("/{listing_id}/scenario", response_model=ScenarioResponse)
def run_scenario(listing_id: int, scenario: ScenarioRequest, db: Session = Depends(get_db)):
    """Recalculate financials with custom inputs (interactive sliders)."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    analysis = db.query(Analysis).filter(Analysis.listing_id == listing_id).first()

    # Build analysis dict from existing data + overrides
    existing_reno = (analysis.renovation_estimate or {}) if analysis else {}
    existing_arv = (analysis.arv_estimate or {}) if analysis else {}
    existing_rental = (analysis.rental_estimate or {}) if analysis else {}
    existing_council = (analysis.council_rates or {}) if analysis else {}
    existing_insurance = (analysis.insurability or {}) if analysis else {}
    existing_timeline = (analysis.timeline_estimate or {}) if analysis else {}
    existing_subdivision = (analysis.subdivision_analysis or {}) if analysis else {}

    # Apply overrides
    reno_cost = scenario.renovation_budget or existing_reno.get("total_estimated", 60000)
    arv = scenario.sale_price or existing_arv.get("estimated_arv", listing.asking_price * 1.3 if listing.asking_price else 0)
    weekly_rent = scenario.weekly_rent or existing_rental.get("estimated_weekly_rent", 0)
    purchase_price = scenario.purchase_price or listing.asking_price or 0
    interest_rate = scenario.interest_rate
    timeline_weeks = scenario.timeline_weeks or existing_timeline.get("estimated_weeks", 8)

    analysis_dict = {
        "renovation": {"total_estimated": reno_cost, "renovation_level": existing_reno.get("renovation_level", "MODERATE")},
        "arv": {"estimated_arv": arv},
        "rental": {"estimated_weekly_rent": weekly_rent},
        "council": {"annual_rates": existing_council.get("annual_rates", 3000)},
        "insurability": {"annual_insurance": existing_insurance.get("annual_insurance", 2000)},
        "timeline": {"estimated_weeks": timeline_weeks},
    }

    listing_dict = {
        "price_display": purchase_price,
        "bedrooms": listing.bedrooms or 3,
    }

    flip = calculate_flip_financials(listing_dict, analysis_dict, interest_rate_override=interest_rate)
    rental = calculate_rental_financials(listing_dict, analysis_dict, interest_rate_override=interest_rate)
    strategy = decide_strategy(flip, rental, existing_subdivision)

    return ScenarioResponse(
        flip_financials=flip,
        rental_financials=rental,
        strategy_decision=strategy,
    )


@router.get("/{listing_id}/report", response_model=PropertyReport)
def get_property_report(listing_id: int, db: Session = Depends(get_db)):
    """Get the full property report as specified in the algorithm doc."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    analysis = db.query(Analysis).filter(Analysis.listing_id == listing_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    flip = analysis.flip_financials or {}
    rental = analysis.rental_financials or {}
    strategy = analysis.strategy_decision or {}
    reno = analysis.renovation_estimate or {}
    pop = analysis.population_data or {}
    ins = analysis.insurability or {}
    subdiv = analysis.subdivision_analysis or {}
    arv = analysis.arv_estimate or {}
    rental_est = analysis.rental_estimate or {}

    return PropertyReport(
        listing_id=listing.listing_id,
        address=listing.full_address or listing.address,
        listing_url=listing.property_url,
        overall_verdict=analysis.verdict or "PENDING",
        composite_score=analysis.composite_score or 0,
        rank=analysis.rank,
        recommended_strategy={
            "strategy": strategy.get("recommended_strategy", ""),
            "reason": strategy.get("reason", ""),
            "primary_metrics": {
                "flip_roi": flip.get("roi_percentage", 0),
                "rental_yield": rental.get("gross_yield_percentage", 0),
                "subdivision_value": subdiv.get("net_value_add", 0),
            },
        },
        flip_scenario={
            "purchase_price": flip.get("purchase_price", 0),
            "renovation_cost": flip.get("renovation_cost", 0),
            "arv": flip.get("arv", 0),
            "net_profit": flip.get("net_profit", 0),
            "roi": flip.get("roi_percentage", 0),
            "timeline_weeks": flip.get("timeline_weeks", 0),
        },
        rental_scenario={
            "gross_yield": rental.get("gross_yield_percentage", 0),
            "weekly_rent": rental.get("weekly_rent", 0),
            "annual_cashflow": rental.get("overall_annual_cashflow", 0),
            "net_yield": rental.get("net_yield_percentage", 0),
        },
        property={
            "bedrooms": listing.bedrooms,
            "bathrooms": listing.bathrooms,
            "land_area": listing.land_area,
            "floor_area": listing.floor_area,
            "capital_value": listing.capital_value,
        },
        renovation={
            "level": reno.get("renovation_level", ""),
            "estimated_cost": reno.get("total_estimated", 0),
            "timeline_weeks": (analysis.timeline_estimate or {}).get("estimated_weeks", 0),
            "key_items": reno.get("key_items", []),
        },
        location={
            "suburb": listing.suburb,
            "district": listing.district,
            "region": listing.region,
            "population": pop.get("current_pop", 0),
            "growth_rate": pop.get("projected_growth", 0),
        },
        insurability={
            "insurable": ins.get("insurable", True),
            "annual_premium": ins.get("annual_insurance", 0),
            "provider": ins.get("insurer", ""),
        },
        subdivision={
            "potential": subdiv.get("subdivision_potential", False),
            "estimated_value_add": subdiv.get("estimated_uplift", 0),
            "costs": subdiv.get("subdivision_costs", 0),
            "net_value": subdiv.get("net_value_add", 0),
        },
        comparable_sales=arv.get("comparable_sales", []),
        rental_comps=rental_est.get("rental_comps", []),
        flags=analysis.flags or [],
        confidence_level=analysis.confidence_level or "MEDIUM",
        next_steps=analysis.next_steps or [],
    )
