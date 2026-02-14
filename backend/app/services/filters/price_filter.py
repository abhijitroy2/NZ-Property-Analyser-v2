"""Stage 1 Filter: Price check against max budget."""

import logging
from typing import Tuple, Optional, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

REJECT = "REJECT"
PASS = "PASS"


def filter_price(listing) -> Tuple[str, str]:
    """
    Max budget filter. Rejects listings over the configured max price.
    
    Returns:
        Tuple of (status, reason). Status is "PASS" or "REJECT".
    """
    max_price = settings.max_price
    asking_price = listing.asking_price

    if asking_price is None:
        # If we can't determine price, let it through for manual review
        logger.info(f"Listing {listing.listing_id}: No parseable price ('{listing.display_price}'), passing for manual review")
        return PASS, ""

    if asking_price > max_price:
        reason = f"Over budget: ${asking_price:,.0f} > ${max_price:,.0f}"
        logger.info(f"Listing {listing.listing_id}: {reason}")
        return REJECT, reason

    logger.info(f"Listing {listing.listing_id}: Price ${asking_price:,.0f} within budget")
    return PASS, ""
