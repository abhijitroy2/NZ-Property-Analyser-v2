"""
Tenancy Services Bond Data Client.
Fetches rental data from tenancy.govt.nz bond lodgement records.
Falls back to TradeMe estimated rent when unavailable.
"""

import re
import logging
from typing import Dict, Any, Optional, List
from statistics import median

import requests

logger = logging.getLogger(__name__)


class TenancyGovtClient:
    """Client for tenancy.govt.nz bond/rental data."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def get_rental_data(
        self,
        suburb: str,
        bedrooms: int,
        region: str = "",
        property_type: str = "house",
    ) -> Dict[str, Any]:
        """
        Get rental data for a location and bedroom count.
        
        Returns:
            Dict with estimated_weekly_rent, bond_samples, source, etc.
        """
        # Try to fetch from tenancy.govt.nz
        bonds = self._fetch_bond_data(suburb, bedrooms, property_type)

        if len(bonds) < 5 and region:
            # Expand search to region
            bonds = self._fetch_bond_data(region, bedrooms, property_type)

        if bonds:
            weekly_rents = [b["weekly_rent"] for b in bonds if b.get("weekly_rent")]
            if weekly_rents:
                med_rent = median(weekly_rents)
                return {
                    "estimated_weekly_rent": round(med_rent, 2),
                    "bond_samples": len(bonds),
                    "rent_range": {
                        "low": min(weekly_rents),
                        "high": max(weekly_rents),
                    },
                    "source": "tenancy.govt.nz",
                    "rental_comps": bonds[:5],
                }

        # Fallback: no data available from tenancy services
        return {
            "estimated_weekly_rent": None,
            "bond_samples": 0,
            "source": "unavailable",
            "rental_comps": [],
        }

    def _fetch_bond_data(self, location: str, bedrooms: int, property_type: str) -> List[Dict]:
        """
        Attempt to fetch bond data from tenancy.govt.nz.
        
        Note: The real implementation would scrape or use their search tool.
        This is a framework that can be expanded with actual scraping logic.
        """
        try:
            # Tenancy Services has a market rent tool
            url = "https://www.tenancy.govt.nz/rent-bond-and-bills/market-rent/"
            # In production, this would submit the form and parse results
            # For now, return empty to trigger fallback
            logger.debug(f"Bond data lookup for {location}, {bedrooms}br - API integration pending")
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch bond data: {e}")
            return []


def parse_trademe_rent_estimate(rent_string: str) -> Optional[float]:
    """
    Parse TradeMe's estimated weekly rent string into a numeric value.
    Examples: "$550 - $650 per week" -> 600.0
    """
    if not rent_string:
        return None

    # Find all numbers
    numbers = re.findall(r"\$?([\d,]+)", rent_string)
    if not numbers:
        return None

    values = [float(n.replace(",", "")) for n in numbers]

    if len(values) >= 2:
        return (values[0] + values[1]) / 2  # Midpoint of range
    elif len(values) == 1:
        return values[0]

    return None
