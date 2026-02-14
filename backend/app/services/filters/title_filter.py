"""Stage 1 Filter: Title type check - reject unit title, leasehold, cross-lease."""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)

REJECT = "REJECT"
PASS = "PASS"

REJECT_TITLE_TYPES = [
    "unit title",
    "leasehold",
    "cross lease",
    "cross-lease",
]


def filter_title(listing) -> Tuple[str, str]:
    """
    Title type filter. Rejects listings with unit title, leasehold, or cross-lease.
    
    Returns:
        Tuple of (status, reason).
    """
    title_type = (listing.title_type or "").lower().strip()

    if not title_type:
        # Check description for title type mentions
        desc = (listing.description or "").lower()
        title_text = (listing.title or "").lower()
        combined = desc + " " + title_text

        for reject_type in REJECT_TITLE_TYPES:
            if reject_type in combined:
                reason = f"Title type detected in description: {reject_type}"
                logger.info(f"Listing {listing.listing_id}: {reason}")
                return REJECT, reason

        # No title type info - pass for manual review
        return PASS, ""

    for reject_type in REJECT_TITLE_TYPES:
        if reject_type in title_type:
            reason = f"Rejected title type: {title_type}"
            logger.info(f"Listing {listing.listing_id}: {reason}")
            return REJECT, reason

    logger.info(f"Listing {listing.listing_id}: Title type '{title_type}' accepted")
    return PASS, ""
