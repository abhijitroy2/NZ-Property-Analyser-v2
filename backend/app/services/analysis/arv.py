"""
ARV (After Repair Value) Estimation.
Estimates post-renovation property value using comparable sales data.
"""

import re
from typing import Dict, Any, List, Optional
from statistics import median


def estimate_arv(
    listing_data: Dict[str, Any],
    nearby_properties: List[Dict[str, Any]],
    estimated_market_price: str = "",
) -> Dict[str, Any]:
    """
    Estimate After Repair Value using comparable nearby property sales.
    
    Args:
        listing_data: Dict with bedrooms, land_area, floor_area etc.
        nearby_properties: List of nearby sold properties from TradeMe.
        estimated_market_price: TradeMe's market price estimate string.
    
    Returns:
        Dict with ARV estimate and comparables.
    """
    # Parse nearby property prices
    valid_comps = []
    for prop in nearby_properties:
        price = prop.get("price_numeric")
        if price and price > 50000:  # Sanity check
            valid_comps.append(prop)

    comp_prices = [c["price_numeric"] for c in valid_comps if c.get("price_numeric")]

    # Parse TradeMe estimated market price as additional data point
    tm_estimate = _parse_market_estimate(estimated_market_price)

    if comp_prices:
        median_price = median(comp_prices)
        avg_price = sum(comp_prices) / len(comp_prices)

        # For ARV, we want to estimate post-renovation value
        # Use upper quartile of comps (assuming renovated properties sell higher)
        sorted_prices = sorted(comp_prices)
        upper_quartile_idx = len(sorted_prices) * 3 // 4
        upper_price = sorted_prices[upper_quartile_idx] if sorted_prices else median_price

        # Weight: 60% upper quartile comps, 40% median
        estimated_arv = (upper_price * 0.6) + (median_price * 0.4)

        # Adjust for features
        if listing_data.get("land_area") and listing_data["land_area"] > 800:
            estimated_arv += 20000  # Large section premium

        confidence = _calculate_confidence(len(valid_comps), comp_prices, tm_estimate)

        return {
            "estimated_arv": round(estimated_arv, 0),
            "median_comp_price": round(median_price, 0),
            "avg_comp_price": round(avg_price, 0),
            "upper_quartile_price": round(upper_price, 0),
            "comparables_used": len(valid_comps),
            "confidence_score": confidence,
            "trademe_estimate": tm_estimate,
            "comparable_sales": valid_comps[:5],
            "source": "nearby_comparables",
        }

    elif tm_estimate:
        # Fallback to TradeMe estimate
        # Apply a renovation uplift factor (15-25% for moderate reno)
        reno_uplift = 1.15  # Conservative 15% uplift post-renovation
        estimated_arv = tm_estimate * reno_uplift

        return {
            "estimated_arv": round(estimated_arv, 0),
            "median_comp_price": None,
            "avg_comp_price": None,
            "upper_quartile_price": None,
            "comparables_used": 0,
            "confidence_score": 30,  # Low confidence with only TM estimate
            "trademe_estimate": tm_estimate,
            "comparable_sales": [],
            "source": "trademe_estimate_with_uplift",
        }

    else:
        # No data - use asking price with standard uplift
        asking = listing_data.get("asking_price", 0) or 0
        if asking > 0:
            estimated_arv = asking * 1.2  # 20% uplift assumption
        else:
            estimated_arv = 0

        return {
            "estimated_arv": round(estimated_arv, 0),
            "median_comp_price": None,
            "avg_comp_price": None,
            "upper_quartile_price": None,
            "comparables_used": 0,
            "confidence_score": 10,
            "trademe_estimate": None,
            "comparable_sales": [],
            "source": "asking_price_estimate",
        }


def _parse_market_estimate(estimate_str: str) -> Optional[float]:
    """Parse TradeMe's estimated market price range to a single value."""
    if not estimate_str:
        return None

    numbers = re.findall(r"\$?([\d,]+)", estimate_str)
    if not numbers:
        return None

    values = [float(n.replace(",", "")) for n in numbers]
    if len(values) >= 2:
        return (values[0] + values[1]) / 2
    elif len(values) == 1:
        return values[0]
    return None


def _calculate_confidence(num_comps: int, prices: List[float], tm_estimate: Optional[float]) -> float:
    """
    Calculate confidence score (0-100) for the ARV estimate.
    Based on number and consistency of comparables.
    """
    score = 0

    # More comps = more confidence
    if num_comps >= 8:
        score += 40
    elif num_comps >= 5:
        score += 30
    elif num_comps >= 3:
        score += 20
    elif num_comps >= 1:
        score += 10

    # Price consistency (lower variance = more confidence)
    if prices and len(prices) >= 2:
        avg = sum(prices) / len(prices)
        variance = sum((p - avg) ** 2 for p in prices) / len(prices)
        std_dev = variance ** 0.5
        cv = std_dev / avg if avg > 0 else 1  # Coefficient of variation

        if cv < 0.1:
            score += 30  # Very consistent
        elif cv < 0.2:
            score += 20
        elif cv < 0.3:
            score += 10

    # TradeMe estimate available adds confidence
    if tm_estimate:
        score += 15

    # Recency bonus (we already filtered for recent sales)
    score += 15

    return min(100, score)
