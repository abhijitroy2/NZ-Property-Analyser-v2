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


def _parse_market_estimate(est_str: str) -> Optional[float]:
    """
    Parse TradeMe estimated market price (e.g. '$530K - $565K' or '$450,000') to float.
    Handles K suffix (thousands). Returns midpoint for ranges.
    """
    if not est_str or not est_str.strip():
        return None
    text = est_str.strip()
    values = []
    # Match $530K or 530K (thousands) or $450,000 (full number)
    for m in re.finditer(r"\$?\s*([\d,]+)\s*[Kk]?", text):
        num_str = m.group(1).replace(",", "")
        if not num_str:
            continue
        try:
            val = float(num_str)
            # Check if K follows the number (e.g. 530K = 530000)
            end = m.end(1)
            if end < len(text) and text[end : end + 1].upper() == "K":
                val *= 1000
            elif val < 1000:
                val *= 1000
            if val >= 10000:
                values.append(val)
        except ValueError:
            continue
    if not values:
        return None
    return sum(values) / len(values)


def get_effective_asking_price(listing) -> Optional[float]:
    """
    Return the effective purchase price for financial modelling.
    Priority: asking_price -> capital_value -> estimated_market_price.
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
    if listing.estimated_market_price:
        emp_val = _parse_market_estimate(listing.estimated_market_price)
        if emp_val is not None:
            logger.debug(
                f"Listing {listing.listing_id}: Using estimated market price ${emp_val:,.0f}"
            )
            return emp_val
    return None


def filter_price(listing) -> Tuple[str, str]:
    """
    Max budget filter. Rejects listings over the configured max price.
    Fallback order: asking_price -> capital_value -> estimated_market_price.
    """
    max_price = settings.max_price
    asking_price = get_effective_asking_price(listing)

    if asking_price is None:
        logger.info(
            f"Listing {listing.listing_id}: No parseable price "
            f"('{listing.display_price}', CV: '{listing.capital_value}', est: '{listing.estimated_market_price}'), passing for manual review"
        )
        return PASS, ""

    if asking_price > max_price:
        reason = f"Over budget: ${asking_price:,.0f} > ${max_price:,.0f}"
        logger.info(f"Listing {listing.listing_id}: {reason}")
        return REJECT, reason

    logger.info(f"Listing {listing.listing_id}: Price ${asking_price:,.0f} within budget")
    return PASS, ""
