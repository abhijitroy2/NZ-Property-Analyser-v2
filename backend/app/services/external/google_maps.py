"""
Google Maps Geocoding Client.
Used for address normalization and location data.
Falls back to using TradeMe's geographic location when API key not configured.
"""

import logging
from typing import Dict, Any, Optional, Tuple

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class GoogleMapsClient:
    """Client for Google Maps geocoding and location services."""

    def __init__(self):
        self.api_key = settings.google_maps_api_key
        self.enabled = bool(self.api_key)

    def geocode(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Geocode an address to lat/lng coordinates.
        Returns None if API not configured or request fails.
        """
        if not self.enabled:
            return None

        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            resp = requests.get(url, params={
                "address": f"{address}, New Zealand",
                "key": self.api_key,
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                location = result["geometry"]["location"]
                return {
                    "lat": location["lat"],
                    "lng": location["lng"],
                    "formatted_address": result.get("formatted_address", ""),
                }
        except Exception as e:
            logger.warning(f"Geocoding failed for {address}: {e}")

        return None

    def parse_trademe_location(self, geo_string: str) -> Optional[Tuple[float, float]]:
        """
        Parse TradeMe's GeographicLocation string to lat/lng tuple.
        Format: "-36.8485,174.7633" or similar.
        """
        if not geo_string:
            return None

        try:
            parts = geo_string.strip().split(",")
            if len(parts) == 2:
                lat = float(parts[0].strip())
                lng = float(parts[1].strip())
                return (lat, lng)
        except (ValueError, IndexError):
            pass

        return None
