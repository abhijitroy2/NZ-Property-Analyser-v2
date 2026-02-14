"""
Composite Scoring Engine.
Generates weighted composite scores for ranking properties.
Assigns verdicts: STRONG_BUY, BUY, MAYBE, PASS.
"""

from typing import Dict, Any, List


# Scoring weights
WEIGHTS = {
    "roi": 0.40,              # 40% - Most important
    "timeline": 0.15,         # 15% - Speed matters
    "confidence": 0.15,       # 15% - Data quality
    "subdivision": 0.15,      # 15% - Upside potential
    "location_growth": 0.10,  # 10% - Future potential
    "insurability": 0.05,     # 5% - Risk factor
}

# Verdict thresholds
VERDICT_THRESHOLDS = {
    "STRONG_BUY": 75,
    "BUY": 55,
    "MAYBE": 35,
    "PASS": 0,
}


def calculate_composite_score(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate weighted composite score for ranking properties.
    
    Args:
        analysis_data: Dict containing all analysis results with keys:
            - strategy_decision
            - flip (flip financials)
            - rental (rental financials)
            - timeline
            - arv
            - rental_estimate
            - subdivision
            - population
            - insurability
    
    Returns:
        Dict with composite_score, component_scores, verdict, flags, next_steps.
    """
    strategy = analysis_data.get("strategy_decision", {})
    flip = analysis_data.get("flip", {})
    rental = analysis_data.get("rental", {})
    timeline = analysis_data.get("timeline", {})
    arv = analysis_data.get("arv", {})
    rental_est = analysis_data.get("rental_estimate", {})
    subdivision = analysis_data.get("subdivision", {})
    population = analysis_data.get("population", {})
    insurability = analysis_data.get("insurability", {})

    # 1. ROI Score (0-100)
    recommended = strategy.get("recommended_strategy", "PASS")
    if "FLIP" in recommended:
        roi = flip.get("roi_percentage", 0)
        roi_score = min(100, (roi / 30) * 100)  # 30% ROI = perfect score
    elif "RENTAL" in recommended:
        yield_pct = rental.get("gross_yield_percentage", 0)
        roi_score = min(100, (yield_pct / 15) * 100)  # 15% yield = perfect score
    else:
        # Score based on whichever is better
        flip_roi = flip.get("roi_percentage", 0)
        rental_yield = rental.get("gross_yield_percentage", 0)
        roi_score = max(
            min(100, (flip_roi / 30) * 100),
            min(100, (rental_yield / 15) * 100),
        )

    # 2. Timeline Score (0-100)
    weeks = timeline.get("estimated_weeks", 8)
    if weeks <= 8:
        timeline_score = 100
    elif weeks <= 16:
        timeline_score = 100 - ((weeks - 8) * 5)  # Lose 5 pts per week over 8
    else:
        timeline_score = max(0, 60 - (weeks - 16) * 3)

    # 3. Confidence Score (0-100)
    arv_confidence = arv.get("confidence_score", 50)
    rental_samples = rental_est.get("bond_samples", 0)
    confidence_score = (arv_confidence + min(100, rental_samples * 5)) / 2

    # 4. Subdivision Score (0-100)
    if subdivision.get("subdivision_potential"):
        sub_value = subdivision.get("net_value_add", 0)
        subdivision_score = min(100, (sub_value / 100000) * 100)
    else:
        subdivision_score = 0

    # 5. Location Growth Score (0-100)
    pop_growth = population.get("projected_growth", 0.02) or 0.02
    location_score = min(100, max(0, (pop_growth + 0.05) * 500))

    # 6. Insurability Score (0-100)
    if not insurability.get("insurable", True):
        insurability_score = 0
    else:
        annual_premium = insurability.get("annual_insurance", 2000)
        insurability_score = max(0, 100 - (annual_premium / 30))

    # Calculate composite
    composite = (
        roi_score * WEIGHTS["roi"]
        + timeline_score * WEIGHTS["timeline"]
        + confidence_score * WEIGHTS["confidence"]
        + subdivision_score * WEIGHTS["subdivision"]
        + location_score * WEIGHTS["location_growth"]
        + insurability_score * WEIGHTS["insurability"]
    )

    component_scores = {
        "roi_score": round(roi_score, 1),
        "timeline_score": round(timeline_score, 1),
        "confidence_score": round(confidence_score, 1),
        "subdivision_score": round(subdivision_score, 1),
        "location_score": round(location_score, 1),
        "insurability_score": round(insurability_score, 1),
    }

    # Determine verdict
    verdict = _assign_verdict(composite, strategy)

    # Generate flags
    flags = _generate_flags(analysis_data, component_scores)

    # Generate next steps
    next_steps = _generate_next_steps(verdict, analysis_data)

    # Confidence level
    if confidence_score >= 70:
        confidence_level = "HIGH"
    elif confidence_score >= 40:
        confidence_level = "MEDIUM"
    else:
        confidence_level = "LOW"

    return {
        "composite_score": round(composite, 1),
        "component_scores": component_scores,
        "weights": WEIGHTS,
        "verdict": verdict,
        "flags": flags,
        "next_steps": next_steps,
        "confidence_level": confidence_level,
    }


def _assign_verdict(composite: float, strategy: Dict[str, Any]) -> str:
    """Assign a verdict based on composite score and strategy viability."""
    recommended = strategy.get("recommended_strategy", "PASS")

    if "PASS" == recommended and composite < 40:
        return "PASS"

    if composite >= VERDICT_THRESHOLDS["STRONG_BUY"]:
        return "STRONG_BUY"
    elif composite >= VERDICT_THRESHOLDS["BUY"]:
        return "BUY"
    elif composite >= VERDICT_THRESHOLDS["MAYBE"]:
        return "MAYBE"
    else:
        return "PASS"


def _generate_flags(analysis_data: Dict[str, Any], scores: Dict[str, float]) -> List[str]:
    """Generate warning flags for the property."""
    flags = []

    timeline = analysis_data.get("timeline", {})
    arv = analysis_data.get("arv", {})
    insurability = analysis_data.get("insurability", {})
    image = analysis_data.get("image_analysis", {})

    if timeline.get("estimated_weeks", 0) > 8:
        flags.append(f"Timeline exceeds 8 week target ({timeline['estimated_weeks']} weeks)")

    if scores.get("confidence_score", 0) < 40:
        flags.append("Low confidence - limited comparable data")

    comps_used = arv.get("comparables_used", 0)
    if 0 < comps_used < 3:
        flags.append(f"Limited comparable sales (only {comps_used} in area)")

    if not insurability.get("insurable", True):
        flags.append("Property may be uninsurable")

    premium = insurability.get("annual_insurance", 0)
    if premium > 3500:
        flags.append(f"High insurance premium (${premium:,.0f}/year)")

    structural = image.get("structural_concerns", [])
    if structural:
        flags.append(f"Structural concerns detected: {', '.join(structural[:3])}")

    reno_level = image.get("overall_reno_level", "")
    if reno_level in ("MAJOR", "FULL_GUT"):
        flags.append(f"Significant renovation required ({reno_level})")

    return flags


def _generate_next_steps(verdict: str, analysis_data: Dict[str, Any]) -> List[str]:
    """Generate recommended next steps based on verdict."""
    steps = []

    if verdict in ("STRONG_BUY", "BUY"):
        steps.append("Request building report")
        steps.append("Get property manager rental appraisal")
        steps.append("View property in person")

        if analysis_data.get("subdivision", {}).get("subdivision_potential"):
            steps.append("Check council for subdivision feasibility")

        confidence = analysis_data.get("arv", {}).get("confidence_score", 50)
        if confidence < 50:
            steps.append("Get independent valuation for ARV confidence")

        steps.append("Review title and LIM report")
        steps.append("Prepare offer strategy")

    elif verdict == "MAYBE":
        steps.append("Monitor listing for price reduction")
        steps.append("View property if time permits")
        steps.append("Research area further")

    else:
        steps.append("Skip - does not meet investment criteria")

    return steps


def rank_analyses(analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rank a list of analyses by composite score (descending)."""
    sorted_analyses = sorted(
        analyses,
        key=lambda a: a.get("composite_score", 0),
        reverse=True,
    )
    for i, analysis in enumerate(sorted_analyses, 1):
        analysis["rank"] = i
    return sorted_analyses
