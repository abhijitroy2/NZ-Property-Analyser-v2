"""Stage 1 Filter: Property type / demand profiling (soft filter - does not reject)."""

import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

PASS = "PASS"

# Demand profiles by area type
# These are simplified heuristics; in production, would be driven by actual rental/sales data
STUDENT_TOWNS = [
    "dunedin", "palmerston north", "hamilton", "wellington", "christchurch",
    "lincoln", "massey", "albany",
]

FAMILY_AREAS = [
    "tauranga", "hamilton", "christchurch", "auckland", "napier", "hastings",
    "new plymouth", "whangarei", "kapiti coast", "selwyn", "waimakariri",
    "western bay of plenty",
]

RETIREMENT_AREAS = [
    "tauranga", "kapiti coast", "nelson", "queenstown-lakes",
    "thames-coromandel", "whangarei",
]


def filter_property_type(listing) -> Tuple[str, str, Dict[str, Any]]:
    """
    Property type demand profiling. This is a soft filter - it doesn't reject,
    but provides demand context for scoring.
    
    Returns:
        Tuple of (status, reason, demand_profile).
    """
    bedrooms = listing.bedrooms or 3
    suburb = (listing.suburb or "").lower()
    district = (listing.district or "").lower()
    region = (listing.region or "").lower()

    location = f"{suburb} {district} {region}"

    profile = {
        "is_student_town": False,
        "is_family_area": False,
        "is_retirement_area": False,
        "bedroom_demand_match": True,
        "demand_notes": [],
    }

    # Check location types
    for town in STUDENT_TOWNS:
        if town in location:
            profile["is_student_town"] = True
            profile["demand_notes"].append(f"Student town ({town})")
            break

    for area in FAMILY_AREAS:
        if area in location:
            profile["is_family_area"] = True
            profile["demand_notes"].append(f"Family area ({area})")
            break

    for area in RETIREMENT_AREAS:
        if area in location:
            profile["is_retirement_area"] = True
            profile["demand_notes"].append(f"Retirement area ({area})")
            break

    # Check bedroom demand match
    if profile["is_student_town"]:
        # Student towns: multi-bedroom (3+) is great for flatting
        if bedrooms >= 3:
            profile["demand_notes"].append(f"{bedrooms}br ideal for student flatting")
        else:
            profile["bedroom_demand_match"] = False
            profile["demand_notes"].append(f"{bedrooms}br less ideal in student town (3+ preferred)")

    elif profile["is_family_area"]:
        # Family areas: 3br is the sweet spot
        if bedrooms >= 3:
            profile["demand_notes"].append(f"{bedrooms}br matches family demand")
        else:
            profile["demand_notes"].append(f"{bedrooms}br - smaller than typical family demand")

    elif profile["is_retirement_area"]:
        # Retirement: 2-3br is common
        if 2 <= bedrooms <= 3:
            profile["demand_notes"].append(f"{bedrooms}br suits retirement area demand")

    # Default demand note
    if not profile["demand_notes"]:
        profile["demand_notes"].append(f"{bedrooms}br in {district or region}")

    logger.info(f"Listing {listing.listing_id}: Demand profile: {', '.join(profile['demand_notes'])}")
    return PASS, "", profile
