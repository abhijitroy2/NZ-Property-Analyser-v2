"""
Strategy Decision Logic.
Determines optimal strategy: FLIP, RENTAL, or PASS based on financial analysis.
"""

from typing import Dict, Any


def decide_strategy(
    flip_analysis: Dict[str, Any],
    rental_analysis: Dict[str, Any],
    subdivision_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Determine optimal strategy based on flip ROI, rental yield, and subdivision potential.
    
    Args:
        flip_analysis: Results from calculate_flip_financials.
        rental_analysis: Results from calculate_rental_financials.
        subdivision_analysis: Results from subdivision analysis service.
    
    Returns:
        Dict with recommended strategy and reasoning.
    """
    flip_roi = flip_analysis.get("roi_percentage", 0)
    rental_yield = rental_analysis.get("gross_yield_percentage", 0)

    recommended = "PASS"
    reason = ""

    if flip_roi >= 15:
        if rental_yield >= 9:
            # Both viable - compare
            if flip_roi > (rental_yield * 1.5):
                recommended = "FLIP"
                reason = f"Higher ROI: {flip_roi:.1f}% vs {rental_yield:.1f}% yield"
            else:
                recommended = "RENTAL"
                reason = f"Good rental yield {rental_yield:.1f}% with long-term appreciation"
        else:
            recommended = "FLIP"
            reason = f"ROI {flip_roi:.1f}% meets target, yield {rental_yield:.1f}% below 9%"

    elif rental_yield >= 9:
        recommended = "RENTAL"
        reason = f"Rental yield {rental_yield:.1f}% meets target, flip ROI {flip_roi:.1f}% below 15%"

    else:
        recommended = "PASS"
        reason = f"Neither strategy meets targets (Flip: {flip_roi:.1f}%, Rental: {rental_yield:.1f}%)"

    # Factor in subdivision potential
    subdivision_potential = subdivision_analysis.get("subdivision_potential", False)
    subdivision_value = subdivision_analysis.get("net_value_add", 0)

    if subdivision_potential and subdivision_value > 0:
        recommended += "_WITH_SUBDIVISION"
        reason += f" | Subdivision adds ~${subdivision_value:,.0f}"

    return {
        "recommended_strategy": recommended,
        "reason": reason,
        "flip_roi": round(flip_roi, 2),
        "rental_yield": round(rental_yield, 2),
        "subdivision_bonus": subdivision_value,
    }
