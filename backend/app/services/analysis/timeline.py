"""
Timeline Estimation.
Estimates renovation timeline in weeks based on renovation level.
"""

from typing import Dict, Any

# Typical timelines (weeks on tools, excluding consents)
TIMELINES = {
    "NONE": 0,
    "COSMETIC": 2,
    "MODERATE": 6,
    "MAJOR": 12,
    "FULL_GUT": 20,
}


def estimate_timeline(renovation_estimate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estimate renovation timeline in weeks.
    
    Args:
        renovation_estimate: Dict from estimate_renovation_cost with renovation_level.
    
    Returns:
        Dict with timeline details.
    """
    reno_level = renovation_estimate.get("renovation_level", "MODERATE")
    estimated_weeks = TIMELINES.get(reno_level, 8)

    # Adjust for additional structural work
    additional = renovation_estimate.get("additional_items", 0)
    if additional > 20000:
        estimated_weeks += 2  # Extra time for significant additional work
    if additional > 40000:
        estimated_weeks += 2  # Even more for major structural work

    within_target = estimated_weeks <= 8

    return {
        "estimated_weeks": estimated_weeks,
        "within_8_week_target": within_target,
        "renovation_level": reno_level,
        "notes": _get_timeline_notes(reno_level, estimated_weeks),
    }


def _get_timeline_notes(reno_level: str, weeks: int) -> str:
    if reno_level == "NONE" or weeks == 0:
        return "No renovation required"
    elif weeks <= 4:
        return "Quick turnaround - cosmetic work only"
    elif weeks <= 8:
        return "Within 8-week target - manageable renovation"
    elif weeks <= 12:
        return "Exceeds 8-week target - moderate complexity"
    elif weeks <= 16:
        return "Significant renovation - plan for extended holding costs"
    else:
        return "Major renovation - consider phased approach or adjust expectations"
