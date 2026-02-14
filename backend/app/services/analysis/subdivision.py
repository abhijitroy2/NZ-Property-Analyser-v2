"""
Subdivision Potential Analysis.
Checks if a property has subdivision potential based on land area and zoning.
"""

from typing import Dict, Any

from app.services.external.council_api import CouncilAPIClient

# Minimum land areas for subdivision by zone type
MIN_AREAS = {
    "RESIDENTIAL_SINGLE": 600,
    "RESIDENTIAL_MIXED": 400,
    "RESIDENTIAL_MEDIUM": 300,
    "RESIDENTIAL_HIGH": 200,
}


def analyze_subdivision_potential(
    listing_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Check if property has subdivision potential.
    
    Args:
        listing_data: Dict with land_area, address, district, asking_price.
    
    Returns:
        Dict with subdivision analysis.
    """
    land_area = listing_data.get("land_area")
    address = listing_data.get("address", "")
    district = listing_data.get("district", "")
    asking_price = listing_data.get("asking_price", 0) or 0

    if not land_area:
        return {
            "subdivision_potential": False,
            "reason": "Land area unknown",
            "value_uplift": 0,
            "net_value_add": 0,
        }

    # Get zoning info
    council_client = CouncilAPIClient()
    zoning_info = council_client.get_zoning(address, district)
    zoning = zoning_info.get("zoning", "RESIDENTIAL_SINGLE")

    min_required = MIN_AREAS.get(zoning, 600)

    # Need enough land for at least 2 lots
    subdivision_possible = land_area >= min_required * 2

    if not subdivision_possible:
        return {
            "subdivision_potential": False,
            "reason": f"Insufficient land: {land_area}sqm (need {min_required * 2}sqm for {zoning})",
            "land_area": land_area,
            "zoning": zoning,
            "min_lot_size": min_required,
            "value_uplift": 0,
            "subdivision_costs": 0,
            "net_value_add": 0,
        }

    # Estimate value uplift from subdivision
    # Rough estimate: extra lot worth ~60% of current land value
    land_value = asking_price * 0.3 if asking_price > 0 else 100000  # Assume 30% is land
    subdivision_uplift = land_value * 0.6

    # Subdivision costs (survey, consents, legals, services)
    subdivision_costs = 80000

    net_value = subdivision_uplift - subdivision_costs

    # Calculate how many extra lots
    extra_lots = int(land_area / min_required) - 1

    return {
        "subdivision_potential": True,
        "land_area": land_area,
        "zoning": zoning,
        "min_lot_size": min_required,
        "extra_lots_possible": extra_lots,
        "estimated_uplift": round(subdivision_uplift, 0),
        "subdivision_costs": subdivision_costs,
        "net_value_add": round(net_value, 0),
        "reason": f"Land {land_area}sqm allows ~{extra_lots} additional lot(s) in {zoning} zone",
    }
