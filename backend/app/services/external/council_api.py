"""
Council Rates & Zoning API Client.
Fetches council rates and zoning data. Uses council zone APIs when in scope.
"""

import logging
from typing import Dict, Any, Optional

from app.config import settings
from app.services.external.google_maps import GoogleMapsClient
from app.services.external.zone_api import resolve_council, get_zone_at_point, get_rules_for_zone

logger = logging.getLogger(__name__)

# Average rates by district (NZ annual council rates estimates 2024/2025)
# These are rough averages and vary significantly by property value
AVERAGE_RATES_BY_DISTRICT = {
    "auckland": 3500,
    "hamilton city": 3200,
    "hamilton": 3200,
    "tauranga city": 3800,
    "tauranga": 3800,
    "wellington city": 4200,
    "wellington": 4200,
    "christchurch city": 3000,
    "christchurch": 3000,
    "dunedin city": 3400,
    "dunedin": 3400,
    "palmerston north city": 3100,
    "palmerston north": 3100,
    "napier city": 3300,
    "napier": 3300,
    "hastings district": 3000,
    "hastings": 3000,
    "nelson city": 3600,
    "nelson": 3600,
    "new plymouth district": 3200,
    "new plymouth": 3200,
    "rotorua district": 3400,
    "rotorua": 3400,
    "whangarei district": 2800,
    "whangarei": 2800,
    "invercargill city": 2600,
    "invercargill": 2600,
    "lower hutt city": 3800,
    "lower hutt": 3800,
    "upper hutt city": 3400,
    "upper hutt": 3400,
    "porirua city": 3600,
    "porirua": 3600,
    "kapiti coast district": 3500,
    "kapiti coast": 3500,
    "waikato district": 2800,
    "waikato": 2800,
    "waipa district": 3000,
    "waipa": 3000,
    "selwyn district": 2800,
    "selwyn": 2800,
    "waimakariri district": 2600,
    "waimakariri": 2600,
    "queenstown-lakes district": 4000,
    "queenstown-lakes": 4000,
    "far north district": 2400,
    "far north": 2400,
    "western bay of plenty district": 3200,
    "western bay of plenty": 3200,
}

# Zoning types by density
DEFAULT_ZONING = "RESIDENTIAL_SINGLE"


class CouncilAPIClient:
    """Client for council rates and zoning data."""

    def get_council_rates(self, address: str, district: str) -> Dict[str, Any]:
        """
        Fetch annual council rates for a property.
        Falls back to district averages when specific data unavailable.
        """
        # Try specific council API (placeholder for real integration)
        rates = self._fetch_specific_rates(address, district)
        if rates:
            return rates

        # Fallback to district average
        key = district.lower().strip()
        annual_rates = AVERAGE_RATES_BY_DISTRICT.get(key, 3000)  # Default $3000

        return {
            "annual_rates": annual_rates,
            "water_charges": 500,  # Typical water rates
            "total_council_costs": annual_rates + 500,
            "source": "district_average",
            "district": district,
        }

    def get_zoning(self, address: str, district: str, region: str = "") -> Dict[str, Any]:
        """
        Get zoning information for a property.
        Uses council zone API when in scope; falls back to default when unavailable.
        """
        zoning = self._fetch_zoning(address, district, region)
        if zoning:
            return zoning

        return {
            "zoning": DEFAULT_ZONING,
            "source": "default",
            "min_lot_size": 600,
        }

    def _fetch_specific_rates(self, address: str, district: str) -> Optional[Dict[str, Any]]:
        """
        Try to fetch specific property rates from council APIs.
        This would be implemented per-council as they have different systems.
        """
        # Placeholder for real council API integration
        # Most councils have online rates search portals that could be scraped
        logger.debug(f"Council rates lookup for {address} in {district} - API integration pending")
        return None

    def _fetch_zoning(self, address: str, district: str, region: str = "") -> Optional[Dict[str, Any]]:
        """
        Fetch zoning from council zone API when in scope.
        Uses zone_api + rules DB for council-aware lookups.
        """
        if not settings.subdivision_use_council_rules:
            return None

        council = resolve_council(district, region)
        if not council or not council.get("in_scope"):
            return None

        council_id = council.get("council_id", "")
        gm_client = GoogleMapsClient()
        listing_data = {
            "address": address,
            "district": district,
            "region": region,
            "full_address": f"{address}, {district}, New Zealand",
        }
        coords = gm_client.get_coordinates(listing_data)
        if not coords:
            return None

        lat, lng = coords
        zone_result = get_zone_at_point(council_id, lat, lng, council)
        zone_code = "default"
        if zone_result:
            zone_code = zone_result.get("zone_code", "default")

        rules = get_rules_for_zone(council_id, zone_code)
        if not rules:
            return None

        min_lot = rules.get("min_lot_sqm", 600)
        return {
            "zoning": zone_code,
            "source": "zone_api",
            "min_lot_size": min_lot,
        }
