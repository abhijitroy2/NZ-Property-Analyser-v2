"""
Renovation Cost Estimation.
Estimates renovation costs based on property details and image analysis.
"""

from typing import Dict, Any, Optional


# Base costs per sqm (NZ 2025 rates)
COSTS_PER_SQM = {
    "COSMETIC": 500,     # Paint, minor fixes, landscaping
    "MODERATE": 1200,    # Kitchen/bathroom refresh, flooring
    "MAJOR": 2000,       # Full kitchen/bath, rewire, replumb
    "FULL_GUT": 3500,    # Strip to frame, full rebuild interior
}

# Default renovation items per level
RENOVATION_ITEMS = {
    "COSMETIC": [
        "Interior paint",
        "Exterior wash & minor touch-ups",
        "Garden tidy",
        "Minor repairs",
    ],
    "MODERATE": [
        "Full interior/exterior paint",
        "Kitchen refresh (benchtops, handles, splashback)",
        "Bathroom update (vanity, taps, mirror)",
        "New floor coverings",
        "Light fixture updates",
    ],
    "MAJOR": [
        "Full kitchen replacement",
        "Full bathroom replacement",
        "Rewire (electrical)",
        "Replumb (plumbing)",
        "Interior/exterior paint",
        "New floor coverings",
        "Insulation upgrade",
    ],
    "FULL_GUT": [
        "Strip to frame",
        "Full rebuild interior",
        "New kitchen",
        "New bathroom(s)",
        "Complete rewire & replumb",
        "New insulation",
        "New linings (GIB)",
        "New floor coverings",
        "Exterior recladding",
    ],
}


def estimate_renovation_cost(
    listing_data: Dict[str, Any],
    image_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Estimate renovation costs based on property size and image analysis.
    
    Args:
        listing_data: Dict with floor_area, land_area, bedrooms etc.
        image_analysis: Dict from vision API with overall_reno_level etc.
    
    Returns:
        Dict with renovation cost breakdown.
    """
    # Get or estimate floor area
    floor_area = listing_data.get("floor_area")
    if not floor_area:
        floor_area = _estimate_floor_area(listing_data)

    reno_level = image_analysis.get("overall_reno_level", "MODERATE")
    if reno_level not in COSTS_PER_SQM:
        reno_level = "MODERATE"

    # Base cost
    base_cost = floor_area * COSTS_PER_SQM[reno_level]

    # Additional costs from image analysis
    additional_costs = 0
    additional_items = []

    structural_concerns = image_analysis.get("structural_concerns", [])

    if image_analysis.get("roof_condition") == "NEEDS_REPLACE":
        roof_area = floor_area * 1.3  # Rough estimate
        roof_cost = roof_area * 80  # $80/sqm for new roof
        additional_costs += roof_cost
        additional_items.append(f"Roof replacement: ${roof_cost:,.0f}")

    if "weatherboard_rot" in structural_concerns or "weatherboard rot" in str(structural_concerns).lower():
        additional_costs += 15000
        additional_items.append("Weatherboard repair: $15,000")

    if "foundation_issues" in structural_concerns or "foundation" in str(structural_concerns).lower():
        additional_costs += 30000
        additional_items.append("Foundation work: $30,000")

    if "moisture_damage" in str(structural_concerns).lower():
        additional_costs += 10000
        additional_items.append("Moisture damage remediation: $10,000")

    total = base_cost + additional_costs

    # Contingency (15%)
    contingency = total * 0.15

    total_estimated = total + contingency

    # Get key items from image analysis or default
    key_items = image_analysis.get("key_renovation_items", []) or RENOVATION_ITEMS.get(reno_level, [])

    return {
        "renovation_level": reno_level,
        "floor_area_used": round(floor_area, 0),
        "cost_per_sqm": COSTS_PER_SQM[reno_level],
        "base_renovation": round(base_cost, 0),
        "additional_items": round(additional_costs, 0),
        "additional_details": additional_items,
        "contingency": round(contingency, 0),
        "total_estimated": round(total_estimated, 0),
        "key_items": key_items,
    }


def _estimate_floor_area(listing_data: Dict[str, Any]) -> float:
    """Estimate floor area when not provided, based on bedrooms."""
    bedrooms = listing_data.get("bedrooms", 3) or 3

    # Typical NZ house sizes by bedroom count
    area_by_bedrooms = {
        1: 60,
        2: 85,
        3: 110,
        4: 140,
        5: 170,
        6: 200,
    }

    return area_by_bedrooms.get(bedrooms, 110)
