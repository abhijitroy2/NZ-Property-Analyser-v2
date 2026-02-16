"""
Google Maps Geocoding Client.
Used for address normalization and location data.
Falls back to using TradeMe's geographic location when API key not configured.
"""

import logging
from typing import Any, Dict, Optional, Tuple

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

    def get_coordinates(self, listing_data: Dict[str, Any]) -> Optional[Tuple[float, float]]:
        """
        Get lat/lng coordinates for a listing. Prefers TradeMe GeographicLocation
        (no API call), else geocodes via Google Maps.

        Args:
            listing_data: Dict with geographic_location, full_address, address, suburb, district.

        Returns:
            (lat, lng) tuple or None.
        """
        geo = listing_data.get("geographic_location", "")
        if geo:
            coords = self.parse_trademe_location(str(geo))
            if coords:
                return coords

        address_parts = [
            listing_data.get("full_address"),
            listing_data.get("address"),
            listing_data.get("suburb"),
            listing_data.get("district"),
        ]
        address = ", ".join(str(p).strip() for p in address_parts if p)
        if not address:
            return None

        result = self.geocode(address)
        if result:
            return (result["lat"], result["lng"])
        return None
