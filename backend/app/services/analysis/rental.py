"""
Rental Income Estimation.
Estimates weekly rent using tenancy bond data and TradeMe estimates.
"""

import re
from typing import Dict, Any, Optional

from app.services.external.tenancy_govt import TenancyGovtClient, parse_trademe_rent_estimate


def estimate_rental_income(
    listing_data: Dict[str, Any],
    trademe_rent_estimate: str = "",
) -> Dict[str, Any]:
    """
    Estimate weekly rental income using multiple data sources.
    
    Priority: 1) Tenancy.govt.nz bond data, 2) TradeMe estimated rent.
    
    Args:
        listing_data: Dict with suburb, bedrooms, region, property_type.
        trademe_rent_estimate: TradeMe's estimated weekly rent string.
    
    Returns:
        Dict with rental income estimates.
    """
    suburb = listing_data.get("suburb", "")
    bedrooms = listing_data.get("bedrooms", 3) or 3
    region = listing_data.get("region", "")
    property_type = listing_data.get("property_type", "house")
    purchase_price = listing_data.get("asking_price", 0) or 0

    # Source 1: Tenancy CSV (Detailed-Monthly-TLA-Tenancy) bond data
    district = listing_data.get("district", "")
    tenancy_client = TenancyGovtClient()
    tenancy_data = tenancy_client.get_rental_data(
        suburb=suburb,
        bedrooms=bedrooms,
        region=region,
        property_type=property_type,
        district=district,
    )

    # Source 2: TradeMe estimated rent
    tm_rent = parse_trademe_rent_estimate(trademe_rent_estimate)

    # Blend tenancy (district median) and TradeMe (property-specific) when both available.
    # Use midpoint to avoid overestimating: tenancy is TLA-level, TradeMe is property-specific.
    tenancy_rent = tenancy_data.get("estimated_weekly_rent")

    if tenancy_rent and tm_rent:
        weekly_rent = (tenancy_rent + tm_rent) / 2
        source = "tenancy_csv_and_trademe_midpoint"
    elif tenancy_rent:
        weekly_rent = tenancy_rent
        source = "tenancy_csv"
    elif tm_rent:
        weekly_rent = tm_rent
        source = "trademe_estimate"
    else:
        # Fallback: estimate from bedroom count (rough NZ averages)
        weekly_rent = _estimate_from_bedrooms(bedrooms, suburb, region)
        source = "bedroom_estimate"

    # Indicative yield based on purchase price only (pre-renovation).
    # The definitive yield calculation lives in rental_model.py and uses
    # total_invested (purchase + costs + renovation).
    annual_rent = weekly_rent * 50  # 50 weeks to match rental_model vacancy assumption
    indicative_yield = (annual_rent / purchase_price * 100) if purchase_price > 0 else 0

    return {
        "estimated_weekly_rent": round(weekly_rent, 2),
        "annual_rent": round(annual_rent, 2),
        "indicative_yield_percentage": round(indicative_yield, 2),
        "bond_samples": tenancy_data.get("bond_samples", 0),
        "trademe_estimate": tm_rent,
        "tenancy_estimate": tenancy_rent,
        "source": source,
        "rental_comps": tenancy_data.get("rental_comps", []),
    }


def _estimate_from_bedrooms(bedrooms: int, suburb: str, region: str) -> float:
    """Rough rental estimate based on bedroom count and region."""
    # Average NZ weekly rents by bedroom (2024/2025 estimates)
    base_rents = {
        1: 350,
        2: 450,
        3: 550,
        4: 650,
        5: 750,
        6: 850,
    }

    base = base_rents.get(bedrooms, 550)

    # Regional adjustments
    region_lower = region.lower()
    if "auckland" in region_lower:
        return base * 1.30
    elif "wellington" in region_lower:
        return base * 1.15
    elif "canterbury" in region_lower or "christchurch" in region_lower:
        return base * 1.05
    elif "bay of plenty" in region_lower or "tauranga" in region_lower:
        return base * 1.10
    elif "waikato" in region_lower:
        return base * 1.00
    elif "otago" in region_lower or "queenstown" in region_lower:
        return base * 1.20
    else:
        return base * 0.90  # Smaller regions typically cheaper
