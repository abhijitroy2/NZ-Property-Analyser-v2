"""Stage 1 Filter: Population check - min 50k in territorial authority + growth trajectory."""

import logging
from typing import Tuple, Dict, Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

REJECT = "REJECT"
PASS = "PASS"

# NZ Territorial Authority populations (2024 estimates from Stats NZ).
# This is used as a fallback when the Stats NZ API is unavailable.
# Key: district name (lowercase), Value: estimated population
NZ_TA_POPULATIONS = {
    # Major cities / metro areas
    "auckland": 1_720_000,
    "christchurch city": 394_000,
    "christchurch": 394_000,
    "wellington city": 215_000,
    "wellington": 215_000,
    "hamilton city": 180_000,
    "hamilton": 180_000,
    "tauranga city": 160_000,
    "tauranga": 160_000,
    "lower hutt city": 112_000,
    "lower hutt": 112_000,
    "dunedin city": 134_000,
    "dunedin": 134_000,
    "palmerston north city": 90_000,
    "palmerston north": 90_000,
    "napier city": 67_000,
    "napier": 67_000,
    "hastings district": 88_000,
    "hastings": 88_000,
    "nelson city": 54_000,
    "nelson": 54_000,
    "new plymouth district": 87_000,
    "new plymouth": 87_000,
    "rotorua district": 77_000,
    "rotorua": 77_000,
    "whangarei district": 100_000,
    "whangarei": 100_000,
    "invercargill city": 57_000,
    "invercargill": 57_000,
    "upper hutt city": 46_000,
    "upper hutt": 46_000,
    "porirua city": 60_000,
    "porirua": 60_000,
    "kapiti coast district": 57_000,
    "kapiti coast": 57_000,
    "whanganui district": 48_000,
    "whanganui": 48_000,
    "gisborne district": 52_000,
    "gisborne": 52_000,

    # Waikato region districts
    "waikato district": 80_000,
    "waikato": 80_000,
    "waipa district": 58_000,
    "waipa": 58_000,
    "matamata-piako district": 37_000,
    "matamata-piako": 37_000,
    "south waikato district": 26_000,
    "south waikato": 26_000,
    "thames-coromandel district": 32_000,
    "thames-coromandel": 32_000,
    "hauraki district": 21_000,
    "hauraki": 21_000,
    "otorohanga district": 10_600,
    "otorohanga": 10_600,
    "waitomo district": 9_800,
    "waitomo": 9_800,

    # Bay of Plenty
    "western bay of plenty district": 56_000,
    "western bay of plenty": 56_000,
    "whakatane district": 37_000,
    "whakatane": 37_000,
    "kawerau district": 7_500,
    "kawerau": 7_500,
    "opotiki district": 10_200,
    "opotiki": 10_200,

    # Canterbury
    "selwyn district": 76_000,
    "selwyn": 76_000,
    "waimakariri district": 68_000,
    "waimakariri": 68_000,
    "timaru district": 49_000,
    "timaru": 49_000,
    "ashburton district": 36_000,
    "ashburton": 36_000,

    # Other
    "queenstown-lakes district": 47_000,
    "queenstown-lakes": 47_000,
    "queenstown": 47_000,
    "taupo district": 40_000,
    "taupo": 40_000,
    "horowhenua district": 36_000,
    "horowhenua": 36_000,
    "wairoa district": 8_900,
    "wairoa": 8_900,
    "central hawke's bay district": 15_000,
    "central hawke's bay": 15_000,
    "rangitikei district": 16_000,
    "rangitikei": 16_000,
    "ruapehu district": 13_000,
    "ruapehu": 13_000,
    "manawatu district": 32_000,
    "manawatu": 32_000,
    "tararua district": 19_000,
    "tararua": 19_000,
    "south taranaki district": 28_000,
    "south taranaki": 28_000,
    "stratford district": 10_000,
    "stratford": 10_000,
    "far north district": 72_000,
    "far north": 72_000,
    "kaipara district": 26_000,
    "kaipara": 26_000,
    "marlborough district": 51_000,
    "marlborough": 51_000,
    "tasman district": 58_000,
    "tasman": 58_000,
    "buller district": 10_000,
    "buller": 10_000,
    "grey district": 14_000,
    "grey": 14_000,
    "westland district": 8_900,
    "westland": 8_900,
    "hurunui district": 13_500,
    "hurunui": 13_500,
    "kaikoura district": 4_100,
    "kaikoura": 4_100,
    "mackenzie district": 5_200,
    "mackenzie": 5_200,
    "waimate district": 8_200,
    "waimate": 8_200,
    "waitaki district": 24_000,
    "waitaki": 24_000,
    "central otago district": 25_000,
    "central otago": 25_000,
    "clutha district": 18_000,
    "clutha": 18_000,
    "southland district": 33_000,
    "southland": 33_000,
    "gore district": 13_000,
    "gore": 13_000,
    "chatham islands territory": 700,
    "chatham islands": 700,
}

# Growth estimates (simple multiplier: >1 = growing, <1 = declining)
NZ_TA_GROWTH = {
    "auckland": 1.08,
    "hamilton city": 1.12,
    "hamilton": 1.12,
    "tauranga city": 1.15,
    "tauranga": 1.15,
    "christchurch city": 1.06,
    "christchurch": 1.06,
    "wellington city": 1.03,
    "wellington": 1.03,
    "selwyn district": 1.20,
    "selwyn": 1.20,
    "waimakariri district": 1.12,
    "waimakariri": 1.12,
    "queenstown-lakes district": 1.18,
    "queenstown-lakes": 1.18,
    "waikato district": 1.10,
    "waikato": 1.10,
    "western bay of plenty district": 1.08,
    "western bay of plenty": 1.08,
    "kapiti coast district": 1.06,
    "kapiti coast": 1.06,
    "whangarei district": 1.05,
    "whangarei": 1.05,
}


def _get_population(district: str) -> Optional[int]:
    """Look up population for a district. Returns None if unknown."""
    key = district.lower().strip()
    return NZ_TA_POPULATIONS.get(key)


def _get_growth_rate(district: str) -> float:
    """Get projected growth rate. Returns 1.0 (neutral) if unknown."""
    key = district.lower().strip()
    return NZ_TA_GROWTH.get(key, 1.02)  # Default to slight growth


def filter_population(listing) -> Tuple[str, str, Dict[str, Any]]:
    """
    Population filter. Requires minimum population in the territorial authority
    and positive or neutral growth trajectory.
    
    Returns:
        Tuple of (status, reason, population_data).
    """
    min_pop = settings.min_population
    district = listing.district or ""
    region = listing.region or ""

    # Try district first, then region
    population = _get_population(district) or _get_population(region)

    if population is None:
        # Unknown area - pass with warning
        logger.warning(f"Listing {listing.listing_id}: Unknown population for '{district}' / '{region}', passing")
        return PASS, "", {
            "current_pop": None,
            "district": district,
            "region": region,
            "growth_rate": None,
            "note": "Population data unavailable",
        }

    growth_rate = _get_growth_rate(district) or _get_growth_rate(region)
    projected_growth = growth_rate - 1.0  # Convert to percentage change

    pop_data = {
        "current_pop": population,
        "district": district,
        "region": region,
        "growth_rate": growth_rate,
        "projected_growth": projected_growth,
    }

    if population < min_pop:
        reason = f"Population {population:,} below {min_pop:,} threshold ({district})"
        logger.info(f"Listing {listing.listing_id}: {reason}")
        return REJECT, reason, pop_data

    if growth_rate < 0.98:  # Declining by more than 2%
        reason = f"Declining population in {district} (growth rate: {growth_rate:.2f})"
        logger.info(f"Listing {listing.listing_id}: {reason}")
        return REJECT, reason, pop_data

    logger.info(f"Listing {listing.listing_id}: Population {population:,} OK, growth {projected_growth:.1%}")
    return PASS, "", pop_data
