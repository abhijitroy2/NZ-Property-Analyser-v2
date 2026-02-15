"""
Strategy Decision Logic.
Determines optimal strategy: FLIP, RENTAL, or PASS based on financial analysis,
risk tolerance, and market conditions.
"""

from typing import Dict, Any, Optional, List


def decide_strategy(
    flip_analysis: Dict[str, Any],
    rental_analysis: Dict[str, Any],
    subdivision_analysis: Dict[str, Any],
    market_conditions: Optional[Dict[str, Any]] = None,
    risk_tolerance: str = "MODERATE",
) -> Dict[str, Any]:
    """
    Determine optimal strategy based on flip ROI, rental yield, subdivision
    potential, market conditions, and investor risk tolerance.

    Args:
        flip_analysis: Results from calculate_flip_financials.
        rental_analysis: Results from calculate_rental_financials.
        subdivision_analysis: Results from subdivision analysis service.
        market_conditions: Optional dict with 'trend' (HEATING/STABLE/COOLING)
                           and other market signals.
        risk_tolerance: LOW, MODERATE, or HIGH — adjusts decision thresholds.

    Returns:
        Dict with recommended strategy, reasoning, and risk assessment.
    """
    flip_roi = flip_analysis.get("roi_percentage", 0)
    rental_yield = rental_analysis.get("gross_yield_percentage", 0)
    flip_timeline = flip_analysis.get("timeline_weeks", 0)

    # --- Risk-adjusted thresholds ---
    if risk_tolerance == "LOW":
        flip_roi_threshold = 18    # Conservative: higher bar for flips
        rental_yield_threshold = 10
    elif risk_tolerance == "HIGH":
        flip_roi_threshold = 12    # Aggressive: lower bar, accept more risk
        rental_yield_threshold = 8
    else:  # MODERATE (default)
        flip_roi_threshold = 15
        rental_yield_threshold = 9

    # --- Market condition adjustments ---
    market_favors_flip = True
    if market_conditions:
        trend = market_conditions.get("trend", "STABLE")
        if trend == "COOLING":
            market_favors_flip = False
            rental_yield_threshold -= 0.5   # Slightly more lenient on rental
        elif trend == "HEATING":
            flip_roi_threshold -= 1         # Slightly easier to justify a flip

    # --- Decision logic ---
    recommended = "PASS"
    reason = ""

    if flip_roi >= flip_roi_threshold:
        if rental_yield >= rental_yield_threshold:
            # Both strategies viable — compare with market awareness
            if flip_roi > (rental_yield * 1.5) and market_favors_flip:
                recommended = "FLIP"
                reason = (
                    f"Higher ROI: {flip_roi:.1f}% vs {rental_yield:.1f}% yield"
                )
            else:
                recommended = "RENTAL"
                reason = (
                    f"Good rental yield {rental_yield:.1f}% with lower risk & flexibility"
                )
        else:
            if market_favors_flip:
                recommended = "FLIP"
                reason = (
                    f"ROI {flip_roi:.1f}% meets target, yield {rental_yield:.1f}% "
                    f"below {rental_yield_threshold}%"
                )
            else:
                recommended = "PASS"
                reason = (
                    f"ROI {flip_roi:.1f}% meets target but cooling market "
                    f"increases flip risk"
                )

    elif rental_yield >= rental_yield_threshold:
        recommended = "RENTAL"
        reason = (
            f"Rental yield {rental_yield:.1f}% meets target (safer strategy); "
            f"flip ROI {flip_roi:.1f}% below {flip_roi_threshold}%"
        )

    else:
        recommended = "PASS"
        reason = (
            f"Neither strategy meets targets "
            f"(Flip: {flip_roi:.1f}% < {flip_roi_threshold}%, "
            f"Rental: {rental_yield:.1f}% < {rental_yield_threshold}%)"
        )

    # --- Subdivision bonus ---
    subdivision_potential = subdivision_analysis.get("subdivision_potential", False)
    subdivision_value = subdivision_analysis.get("net_value_add", 0)

    if subdivision_potential and subdivision_value > 0:
        recommended += "_WITH_SUBDIVISION"
        reason += f" | Subdivision adds ~${subdivision_value:,.0f}"

    # --- Risk assessment ---
    risk_assessment = _assess_risk(flip_roi, rental_yield, flip_timeline)

    return {
        "recommended_strategy": recommended,
        "reason": reason,
        "flip_roi": round(flip_roi, 2),
        "rental_yield": round(rental_yield, 2),
        "subdivision_bonus": subdivision_value,
        "risk_tolerance": risk_tolerance,
        "risk_assessment": risk_assessment,
    }


def _assess_risk(
    flip_roi: float,
    rental_yield: float,
    timeline_weeks: int,
) -> List[str]:
    """Return a list of risk notes based on the deal fundamentals."""
    risks: List[str] = []

    if timeline_weeks > 12:
        risks.append("Extended renovation timeline increases holding costs")
    if flip_roi > 0 and flip_roi < 20:
        risks.append("Moderate flip ROI leaves less margin for unexpected costs")
    if rental_yield > 0 and rental_yield < 8:
        risks.append("Rental yield below ideal for strong cash flow")

    return risks if risks else ["Low risk — strong fundamentals"]
