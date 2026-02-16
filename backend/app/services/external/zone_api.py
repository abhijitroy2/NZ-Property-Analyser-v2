"""
Zone API Client.
Fetches zoning data from council GIS APIs (ArcGIS REST) for subdivision analysis.
Falls back to rules database default when API unavailable.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

# Path to council data files
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "councils"
_COUNCILS_PATH = _DATA_DIR / "councils.json"
_RULES_PATH = _DATA_DIR / "subdivision_rules.json"

# In-memory cache
_councils_data: Optional[Dict] = None
_rules_data: Optional[Dict] = None
_alias_to_council: Optional[Dict[str, Dict]] = None


def _load_councils() -> Dict:
    """Load councils registry."""
    global _councils_data, _alias_to_council
    if _councils_data is not None:
        return _councils_data

    try:
        with open(_COUNCILS_PATH, encoding="utf-8") as f:
            _councils_data = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load councils.json: {e}")
        _councils_data = {"councils": []}

    _alias_to_council = {}
    for council in _councils_data.get("councils", []):
        for alias in council.get("aliases", []):
            key = alias.lower().strip()
            _alias_to_council[key] = council

    return _councils_data


def _load_rules() -> Dict:
    """Load subdivision rules."""
    global _rules_data
    if _rules_data is not None:
        return _rules_data

    try:
        with open(_RULES_PATH, encoding="utf-8") as f:
            _rules_data = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load subdivision_rules.json: {e}")
        _rules_data = {}

    return _rules_data


def resolve_council(district: str, region: str) -> Optional[Dict[str, Any]]:
    """
    Resolve district/region to council config.

    Args:
        district: TradeMe district string (e.g. "Hastings District").
        region: TradeMe region string (e.g. "Hawke's Bay").

    Returns:
        Council dict with council_id, in_scope, zone_api_* or None.
    """
    _load_councils()
    if _alias_to_council is None:
        return None

    # Try district first, then region
    for raw in (district, region):
        if not raw:
            continue
        key = raw.lower().strip()
        council = _alias_to_council.get(key)
        if council:
            return council

    return None


def get_rules_for_zone(council_id: str, zone_code: str) -> Optional[Dict[str, Any]]:
    """
    Look up subdivision rules for a council and zone.

    Args:
        council_id: Council identifier.
        zone_code: Zone code from API or "default".

    Returns:
        Dict with min_lot_sqm, avg_lot_sqm, consent_type, notes or None.
    """
    rules = _load_rules()
    council_rules = rules.get(council_id, {})
    if not council_rules:
        default = rules.get("auckland", {}).get("default") or {"min_lot_sqm": 600, "consent_type": "discretionary", "notes": "Fallback"}
        return default

    # Try exact zone, then default
    zone_rules = council_rules.get(zone_code) or council_rules.get("default")
    return zone_rules


def get_zone_at_point(council_id: str, lat: float, lng: float, council_config: Dict) -> Optional[Dict[str, Any]]:
    """
    Query council zone GIS API for the zone at a point.

    Args:
        council_id: Council identifier.
        lat: Latitude (WGS84).
        lng: Longitude (WGS84).
        council_config: Council config from resolve_council.

    Returns:
        Dict with zone_code, zone_name, source or None.
    """
    api_type = council_config.get("zone_api_type")
    if api_type != "arcgis_rest":
        return None

    url = council_config.get("zone_api_url")
    layer_id = council_config.get("zone_layer_id")
    zone_field = council_config.get("zone_code_field", "ZONE")

    if not url or layer_id is None:
        return None

    query_url = f"{url.rstrip('/')}/{layer_id}/query"

    # ArcGIS uses longitude (x), latitude (y) for geographic
    params = {
        "geometry": json.dumps({"x": lng, "y": lat}),
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "returnGeometry": "false",
        "outFields": zone_field,
        "f": "json",
    }

    try:
        resp = requests.get(query_url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("error"):
            logger.debug(f"Zone API error for {council_id}: {data.get('error')}")
            return None

        features = data.get("features", [])
        if not features:
            logger.debug(f"No zone at point for {council_id}")
            return None

        attrs = features[0].get("attributes", {})
        zone_code = attrs.get(zone_field) or attrs.get("zone_code") or attrs.get("ZONE") or "default"
        zone_name = str(zone_code)

        return {
            "zone_code": zone_code,
            "zone_name": zone_name,
            "source": "api",
        }
    except Exception as e:
        logger.debug(f"Zone API failed for {council_id}: {e}")
        return None
