"""Stage 1 Filter: Price check against max budget."""

import re
import logging
from typing import Tuple, Optional

from app.config import settings

logger = logging.getLogger(__name__)

REJECT = "REJECT"
PASS = "PASS"


def _parse_capital_value(cv: str) -> Optional[float]:
    """Parse capital value string (e.g. '$450,000' or '450000') to float."""
    if not cv:
        return None
    match = re.search(r"[\d,]+\.?\d*", str(cv))
    if match:
        val = float(match.group(0).replace(",", ""))
        if val > 1000:
            return val
    return None


def get_effective_asking_price(listing) -> Optional[float]:
    """
    Return the effective purchase price for financial modelling.
    Uses asking_price when available; otherwise falls back to parsed capital_value.
    Matches the logic used in filter_price for budget checks.
    """
    if listing.asking_price is not None and listing.asking_price > 0:
        return float(listing.asking_price)
    if listing.capital_value:
        cv_val = _parse_capital_value(listing.capital_value)
        if cv_val is not None:
            logger.debug(
                f"Listing {listing.listing_id}: Using capital value ${cv_val:,.0f} (asking_price not set)"
            )
            return cv_val
    return None


def filter_price(listing) -> Tuple[str, str]:
    """
    Max budget filter. Rejects listings over the configured max price.
    When display_price is non-dollar (deadline sale, auction, price by negotiation, etc.),
    asking_price will be None; in that case we fall back to capital_value.
    """
    max_price = settings.max_price
    asking_price = listing.asking_price

    if asking_price is None and listing.capital_value:
        asking_price = _parse_capital_value(listing.capital_value)
        if asking_price is not None:
            logger.info(f"Listing {listing.listing_id}: No asking price ('{listing.display_price}'), using capital value ${asking_price:,.0f}")

    if asking_price is None:
        # If we can't determine price from either source, let it through for manual review
        logger.info(f"Listing {listing.listing_id}: No parseable price ('{listing.display_price}', CV: '{listing.capital_value}'), passing for manual review")
        return PASS, ""

    if asking_price > max_price:
        reason = f"Over budget: ${asking_price:,.0f} > ${max_price:,.0f}"
        logger.info(f"Listing {listing.listing_id}: {reason}")
        return REJECT, reason

    logger.info(f"Listing {listing.listing_id}: Price ${asking_price:,.0f} within budget")
    return PASS, ""
