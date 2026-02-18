"""
Renovation Cost Estimation.
Estimates renovation costs based on property details and image analysis.
"""

from typing import Dict, Any, Optional


# Base costs per sqm (NZ 2025 rates)
COSTS_PER_SQM = {
    "NONE": 0,           # No renovation required
    "COSMETIC": 500,    # Paint, minor fixes, landscaping
    "MODERATE": 1200,   # Kitchen/bathroom refresh, flooring
    "MAJOR": 2000,      # Full kitchen/bath, rewire, replumb
    "FULL_GUT": 3500,   # Strip to frame, full rebuild interior
}

# Default renovation items per level
RENOVATION_ITEMS = {
    "NONE": ["No renovation required"],
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
    key_items_raw = image_analysis.get("key_renovation_items", [])
    structural_concerns = image_analysis.get("structural_concerns", [])

    # Optimistic override: excellent condition + nothing needed = no renovation
    exterior = image_analysis.get("exterior_condition", "")
    interior = image_analysis.get("interior_quality", "")
    if (
        reno_level == "COSMETIC"
        and exterior in ("EXCELLENT", "GOOD")
        and interior == "MODERN"
        and not key_items_raw
        and not structural_concerns
    ):
        reno_level = "NONE"
    elif reno_level not in COSTS_PER_SQM:
        reno_level = "MODERATE"

    # Base cost
    base_cost = floor_area * COSTS_PER_SQM[reno_level]

    # Additional costs from image analysis
    additional_costs = 0
    additional_items = []
    struct_str = str(structural_concerns).lower()

    if image_analysis.get("roof_condition") == "NEEDS_REPLACE":
        roof_area = floor_area * 1.3  # Rough estimate
        roof_cost = roof_area * 80  # $80/sqm for new roof
        additional_costs += roof_cost
        additional_items.append(f"Roof replacement: ${roof_cost:,.0f}")

    if "weatherboard_rot" in structural_concerns or "weatherboard rot" in struct_str:
        additional_costs += 15000
        additional_items.append("Weatherboard repair: $15,000")

    if "foundation_issues" in structural_concerns or "foundation" in struct_str:
        # Shed/outbuilding foundation is typically much cheaper than main house
        if "shed" in struct_str or "outbuilding" in struct_str:
            additional_costs += 5000
            additional_items.append("Shed/outbuilding foundation: $5,000")
        else:
            additional_costs += 30000
            additional_items.append("Foundation work: $30,000")

    if "moisture_damage" in struct_str:
        additional_costs += 10000
        additional_items.append("Moisture damage remediation: $10,000")

    # Healthy Homes (rental compliance) allowance from listing description signals.
    # This is a pragmatic budget line item, not a legal compliance determination.
    hh = image_analysis.get("healthy_homes_text") if isinstance(image_analysis, dict) else None
    hh_allowance, hh_notes = _healthy_homes_allowance(hh or {}, reno_level)
    if hh_allowance > 0:
        additional_costs += hh_allowance
        additional_items.append(f"Healthy Homes compliance allowance: ${hh_allowance:,.0f}")

    total = base_cost + additional_costs

    # Contingency (15%)
    contingency = total * 0.15

    total_estimated = total + contingency

    # Get key items from image analysis or default
    key_items = key_items_raw if key_items_raw else RENOVATION_ITEMS.get(reno_level, [])

    return {
        "renovation_level": reno_level,
        "floor_area_used": round(floor_area, 0),
        "cost_per_sqm": COSTS_PER_SQM[reno_level],
        "base_renovation": round(base_cost, 0),
        "additional_items": round(additional_costs, 0),
        "additional_details": additional_items,
        "healthy_homes_allowance": round(hh_allowance, 0) if hh_allowance else 0,
        "healthy_homes_notes": hh_notes,
        "healthy_homes_confidence": (hh or {}).get("confidence", "LOW") if isinstance(hh, dict) else "LOW",
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


def _healthy_homes_allowance(hh_text: Dict[str, Any], reno_level: str) -> tuple[float, str]:
    """
    Return (allowance_cost_nzd, notes) based on description-derived Healthy Homes signals.

    Conservative by default: if we can't see evidence in the ad, we assume some budget
    may be needed for rental compliance items (heating/ventilation/insulation).
    """
    if reno_level in ("MAJOR", "FULL_GUT"):
        # Large renovations typically include heating/vent/insulation work anyway.
        return 0.0, ""

    if not isinstance(hh_text, dict) or not hh_text.get("present"):
        return 4000.0, "No description signals; include a small rental compliance buffer."

    confidence = (hh_text.get("confidence") or "LOW").upper()
    claims_compliant = bool(hh_text.get("claims_compliant"))
    signals = hh_text.get("signals") or {}

    has_heating = bool(signals.get("has_heating"))
    has_insulation = bool(signals.get("has_insulation"))
    has_ventilation = bool(signals.get("has_ventilation"))
    risk_moisture = bool(
        signals.get("mentions_damp")
        or signals.get("mentions_mould")
        or signals.get("mentions_condensation")
    )

    # Base buffer for common Healthy Homes upgrades (very rough).
    allowance = 4000.0
    notes: list[str] = []

    if claims_compliant and confidence in ("HIGH", "MEDIUM"):
        # Seller explicitly claims compliance; still keep a token amount for minor fixes.
        allowance = 500.0
        notes.append("Description claims Healthy Homes compliance; minimal buffer kept for small fixes.")
    else:
        # Reduce buffer if multiple core elements are mentioned.
        positives = sum([1 if has_heating else 0, 1 if has_insulation else 0, 1 if has_ventilation else 0])
        if positives >= 2:
            allowance = 1500.0
            notes.append("Description mentions multiple Healthy Homes elements; reduced compliance buffer.")
        elif positives == 1:
            allowance = 3000.0
            notes.append("Description mentions one Healthy Homes element; moderate compliance buffer.")
        else:
            notes.append("No clear Healthy Homes elements mentioned; keep a compliance buffer.")

    if risk_moisture:
        allowance += 2000.0
        notes.append("Damp/mould/condensation mentioned; add buffer for ventilation/moisture remediation.")

    # Clamp to sane range
    allowance = max(0.0, min(8000.0, allowance))
    return allowance, " ".join(notes)
