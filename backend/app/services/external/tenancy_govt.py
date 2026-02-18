"""
Tenancy Services Bond Data Client.
Uses Detailed-Monthly-TLA-Tenancy.csv (from tenancy.govt.nz) for median rent by TLA.
Falls back to TradeMe estimated rent when unavailable.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# CSV at project root (backend/../Detailed-Monthly-TLA-Tenancy.csv)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent  # -> backend/
_PROJECT_ROOT = _BACKEND_DIR.parent
_CSV_PATH = _PROJECT_ROOT / "Detailed-Monthly-TLA-Tenancy.csv"

# Cache for loaded CSV data: {location: {median_rent, lodged_bonds, ...}}
_CSV_CACHE: Optional[Dict[str, Dict[str, Any]]] = None
_LATEST_PERIOD: Optional[str] = None


def _load_csv_data() -> tuple[Dict[str, Dict[str, Any]], str]:
    """
    Load CSV and return (location -> data dict, latest_period).
    Uses only the most recent Time Frame. Excludes ALL and NA.
    """
    global _CSV_CACHE, _LATEST_PERIOD
    if _CSV_CACHE is not None:
        return _CSV_CACHE, _LATEST_PERIOD or ""

    if not _CSV_PATH.exists():
        logger.warning(f"Tenancy CSV not found: {_CSV_PATH}")
        _CSV_CACHE = {}
        return {}, ""

    rows_by_period: Dict[str, List[Dict]] = {}
    with open(_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            period = row.get("Time Frame", "").strip()
            loc_id = row.get("Location Id", "").strip()
            location = row.get("Location", "").strip()
            # Skip ALL and NA rows
            if loc_id in ("-99", "-1"):
                continue
            if not location:
                continue
            if period not in rows_by_period:
                rows_by_period[period] = []
            # Parse median rent (strip commas from numeric fields)
            med_str = (row.get("Median Rent") or "").replace(",", "")
            lodged_str = (row.get("Lodged Bonds") or "0").replace(",", "")
            try:
                median_rent = float(med_str) if med_str else None
            except ValueError:
                median_rent = None
            try:
                lodged_bonds = int(lodged_str) if lodged_str else 0
            except ValueError:
                lodged_bonds = 0
            if median_rent is not None:
                rows_by_period[period].append({
                    "location": location,
                    "median_rent": median_rent,
                    "lodged_bonds": lodged_bonds,
                })

    if not rows_by_period:
        _CSV_CACHE = {}
        return {}, ""

    latest = max(rows_by_period.keys())
    rows = rows_by_period[latest]
    lookup = {r["location"]: r for r in rows}
    _CSV_CACHE = lookup
    _LATEST_PERIOD = latest
    logger.info(f"Loaded tenancy CSV: {len(lookup)} TLAs, period {latest}")
    return lookup, latest


def _match_location(data: Dict[str, Dict], district: str, region: str) -> Optional[Dict[str, Any]]:
    """
    Match district/region to a CSV Location.
    CSV has names like "Invercargill City", "Southland District", "Auckland".
    """
    district = (district or "").strip()
    region = (region or "").strip()

    # Build keys to try (case-sensitive match against CSV keys)
    keys_to_try = []
    if district:
        keys_to_try.extend([f"{district} City", f"{district} District", district])
    if region:
        keys_to_try.extend([f"{region} City", f"{region} District", region])
        if region.lower() == "auckland":
            keys_to_try.append("Auckland")

    for key in keys_to_try:
        if key in data:
            return data[key]

    # Case-insensitive fallback
    key_lower_map = {k.lower(): k for k in data}
    for key in keys_to_try:
        if key.lower() in key_lower_map:
            return data[key_lower_map[key.lower()]]

    # Partial match: any Location containing district or region
    d_lower = district.lower() if district else ""
    r_lower = region.lower() if region else ""
    for loc_name, row in data.items():
        loc_lower = loc_name.lower()
        if (d_lower and d_lower in loc_lower) or (r_lower and r_lower in loc_lower):
            return row

    return None


class TenancyGovtClient:
    """Client for tenancy bond data from CSV (Detailed-Monthly-TLA-Tenancy)."""

    def get_rental_data(
        self,
        suburb: str,
        bedrooms: int,
        region: str = "",
        property_type: str = "house",
        district: str = "",
    ) -> Dict[str, Any]:
        """
        Get rental data for a location.
        Uses district and region to match against TLA (Territorial Local Authority) in CSV.
        CSV has one median rent per TLA per month (no bedroom/dwelling breakdown).
        """
        data, period = _load_csv_data()
        if not data:
            return {
                "estimated_weekly_rent": None,
                "bond_samples": 0,
                "source": "unavailable",
                "rental_comps": [],
            }

        match = _match_location(data, district=district or suburb, region=region)
        if not match:
            logger.debug(f"No TLA match for district={district!r}, region={region!r}")
            return {
                "estimated_weekly_rent": None,
                "bond_samples": 0,
                "source": "unavailable",
                "rental_comps": [],
            }

        median_rent = match.get("median_rent")
        lodged = match.get("lodged_bonds", 0)
        return {
            "estimated_weekly_rent": round(median_rent, 2) if median_rent else None,
            "bond_samples": lodged,
            "rent_range": {"low": median_rent, "high": median_rent},  # CSV has no quartiles per match
            "source": "tenancy_csv",
            "rental_comps": [{"location": match.get("location"), "median_rent": median_rent}],
            "period": period,
        }


def parse_trademe_rent_estimate(rent_string: str) -> Optional[float]:
    """
    Parse TradeMe's estimated weekly rent string into a numeric value.
    Examples: "$550 - $650 per week" -> 600.0
    """
    import re
    if not rent_string:
        return None

    numbers = re.findall(r"\$?([\d,]+)", rent_string)
    if not numbers:
        return None

    values = [float(n.replace(",", "")) for n in numbers]

    if len(values) >= 2:
        return (values[0] + values[1]) / 2
    elif len(values) == 1:
        return values[0]

    return None
