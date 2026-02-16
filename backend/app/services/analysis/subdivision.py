"""
Subdivision Potential Analysis.
Checks if a property has subdivision potential based on land area and zoning.
Uses council zone APIs and rules for in-scope councils; fallback logic for others.
"""

import logging
from typing import Dict, Any

from app.config import settings
from app.services.external.google_maps import GoogleMapsClient
from app.services.external.zone_api import (
    resolve_council,
    get_zone_at_point,
    get_rules_for_zone,
)

logger = logging.getLogger(__name__)

# Fallback minimum areas when council rules unavailable
MIN_AREAS = {
    "RESIDENTIAL_SINGLE": 600,
    "RESIDENTIAL_MIXED": 400,
    "RESIDENTIAL_MEDIUM": 300,
    "RESIDENTIAL_HIGH": 200,
}
DEFAULT_MIN = 600


def analyze_subdivision_potential(
    listing_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Check if property has subdivision potential.

    Args:
        listing_data: Dict with land_area, address, district, region, geographic_location, asking_price.

    Returns:
        Dict with subdivision analysis.
    """
    land_area = listing_data.get("land_area")
    address = listing_data.get("address", "")
    district = listing_data.get("district", "")
    region = listing_data.get("region", "")
    asking_price = listing_data.get("asking_price", 0) or 0

    if not land_area:
        return {
            "subdivision_potential": False,
            "reason": "Land area unknown",
            "value_uplift": 0,
            "net_value_add": 0,
        }

    # Resolve council and try enhanced path
    council = resolve_council(district, region)
    min_required = None
    zoning = "RESIDENTIAL_SINGLE"
    zone_code = None
    zone_source = "fallback"
    rules_source = "fallback"

    if council and council.get("in_scope") and settings.subdivision_use_council_rules:
        council_id = council.get("council_id", "")
        rules = get_rules_for_zone(council_id, "default")
        if rules:
            min_required = rules.get("min_lot_sqm")
            rules_source = "rules_db"

        # Try zone API for more specific zoning
        gm_client = GoogleMapsClient()
        coords = gm_client.get_coordinates(listing_data)
        if coords:
            lat, lng = coords
            zone_result = get_zone_at_point(council_id, lat, lng, council)
            if zone_result:
                zone_code = zone_result.get("zone_code", "default")
                zone_source = zone_result.get("source", "api")
                zoning = str(zone_code)
                zone_rules = get_rules_for_zone(council_id, zone_code)
                if zone_rules and zone_rules.get("min_lot_sqm") is not None:
                    min_required = zone_rules["min_lot_sqm"]
                    rules_source = "rules_db"

    if min_required is None:
        min_required = MIN_AREAS.get(zoning, DEFAULT_MIN)

    # Need enough land for at least 2 lots
    subdivision_possible = land_area >= min_required * 2

    if not subdivision_possible:
        return {
            "subdivision_potential": False,
            "reason": f"Insufficient land: {land_area}sqm (need {min_required * 2}sqm for {zoning})",
            "land_area": land_area,
            "zoning": zoning,
            "min_lot_size": min_required,
            "zone_code": zone_code,
            "zone_source": zone_source,
            "rules_source": rules_source,
            "value_uplift": 0,
            "subdivision_costs": 0,
            "net_value_add": 0,
        }

    # Estimate value uplift from subdivision
    land_value = asking_price * 0.3 if asking_price > 0 else 100000
    subdivision_uplift = land_value * 0.6

    subdivision_costs = 80000
    net_value = subdivision_uplift - subdivision_costs
    extra_lots = int(land_area / min_required) - 1

    return {
        "subdivision_potential": True,
        "land_area": land_area,
        "zoning": zoning,
        "min_lot_size": min_required,
        "zone_code": zone_code,
        "zone_source": zone_source,
        "rules_source": rules_source,
        "extra_lots_possible": extra_lots,
        "estimated_uplift": round(subdivision_uplift, 0),
        "subdivision_costs": subdivision_costs,
        "net_value_add": round(net_value, 0),
        "reason": f"Land {land_area}sqm allows ~{extra_lots} additional lot(s) in {zoning} zone",
    }
