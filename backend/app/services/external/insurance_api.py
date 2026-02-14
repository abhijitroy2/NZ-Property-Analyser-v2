"""
Insurance Quote API Client.
Fetches insurance quotes from Initio or other providers.
Uses mock estimates when API access is not configured.
"""

import logging
from typing import Dict, Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class InsuranceAPIClient:
    """Client for insurance quote APIs."""

    def __init__(self):
        self.provider = settings.insurance_provider

    def get_insurance_quote(self, address: str, property_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get insurance quote for a property.
        
        Args:
            address: Property address.
            property_details: Dict with bedrooms, floor_area, year_built, etc.
        
        Returns:
            Dict with annual_insurance, insurer, insurable status.
        """
        if self.provider != "mock":
            quote = self._fetch_real_quote(address, property_details)
            if quote:
                return quote

        # Mock estimate based on property characteristics
        return self._estimate_insurance(address, property_details)

    def _fetch_real_quote(self, address: str, details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetch real quote from insurance API (e.g., Initio)."""
        # Placeholder for real API integration
        logger.debug(f"Insurance quote for {address} - real API integration pending")
        return None

    def _estimate_insurance(self, address: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate insurance cost based on property characteristics.
        NZ residential insurance typically ranges from $1,500 to $4,000+ per year.
        """
        floor_area = details.get("floor_area", 120) or 120
        bedrooms = details.get("bedrooms", 3) or 3

        # Base rate: approximately $15-20 per sqm for NZ residential
        base_rate = 17  # $/sqm per year
        annual_premium = floor_area * base_rate

        # Adjust for size
        if floor_area > 200:
            annual_premium *= 1.1  # Larger homes cost more
        if floor_area < 80:
            annual_premium *= 0.9

        # Minimum floor
        annual_premium = max(annual_premium, 1500)

        # Cap at reasonable maximum
        annual_premium = min(annual_premium, 5000)

        return {
            "annual_insurance": round(annual_premium, 2),
            "insurer": "Estimated",
            "insurable": True,
            "source": "mock_estimate",
            "note": "Set INSURANCE_PROVIDER in .env for real quotes",
        }
