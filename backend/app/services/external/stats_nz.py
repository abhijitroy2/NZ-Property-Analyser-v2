"""
Stats NZ API Client.
Fetches population and demographic data from Stats NZ (infoshare.stats.govt.nz).
Falls back to built-in estimates when API is unavailable.
"""

import logging
from typing import Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)

STATS_NZ_API_BASE = "https://api.stats.govt.nz/opendata/v1"


class StatsNZClient:
    """Client for Stats NZ population and growth data."""

    def __init__(self):
        self.session = requests.Session()

    def get_population(self, territorial_authority: str, year: int = 2024) -> Optional[int]:
        """
        Get population for a territorial authority.
        Falls back to static estimates if API unavailable.
        """
        # Try API first
        pop = self._fetch_from_api(territorial_authority, year)
        if pop is not None:
            return pop

        # Fallback to static data
        from app.services.filters.population_filter import NZ_TA_POPULATIONS
        key = territorial_authority.lower().strip()
        return NZ_TA_POPULATIONS.get(key)

    def get_projected_population(self, territorial_authority: str, year: int = 2030) -> Optional[int]:
        """Get projected population for a future year."""
        current = self.get_population(territorial_authority)
        if current is None:
            return None

        from app.services.filters.population_filter import NZ_TA_GROWTH
        key = territorial_authority.lower().strip()
        growth_rate = NZ_TA_GROWTH.get(key, 1.02)

        # Simple projection
        years_ahead = year - 2024
        projected = current * (growth_rate ** (years_ahead / 5))
        return int(projected)

    def get_population_data(self, territorial_authority: str) -> Dict[str, Any]:
        """Get comprehensive population data for a TA."""
        current = self.get_population(territorial_authority)
        projected_2030 = self.get_projected_population(territorial_authority, 2030)

        from app.services.filters.population_filter import NZ_TA_GROWTH
        key = territorial_authority.lower().strip()
        growth_rate = NZ_TA_GROWTH.get(key, 1.02)

        historical_growth = growth_rate - 1.0  # Simplified
        projected_growth = (projected_2030 - current) / current if current and projected_2030 else 0

        return {
            "current_pop": current,
            "projected_2030": projected_2030,
            "historical_growth": round(historical_growth, 4),
            "projected_growth": round(projected_growth, 4),
            "growth_rate": growth_rate,
            "territorial_authority": territorial_authority,
            "data_source": "static_estimates",
        }

    def _fetch_from_api(self, territorial_authority: str, year: int) -> Optional[int]:
        """Try to fetch from Stats NZ API. Returns None if unavailable."""
        try:
            # Stats NZ has a complex API; this is a simplified attempt
            # In production, would use their specific dataset endpoints
            url = f"{STATS_NZ_API_BASE}/Population"
            resp = self.session.get(url, timeout=10, params={
                "ta": territorial_authority,
                "year": year,
            })
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data.get("population")
        except Exception as e:
            logger.debug(f"Stats NZ API unavailable: {e}")
        return None
