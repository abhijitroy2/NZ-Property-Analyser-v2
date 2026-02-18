"""
Healthy Homes (NZ) text signal extraction.

This module is intentionally heuristic-only (cheap/fast/transparent):
- It does NOT attempt to determine legal compliance with certainty.
- It extracts seller-claimed signals and risk mentions from listing description text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class _Match:
    key: str
    phrase: str


def _find_any(text: str, phrases: List[str]) -> Tuple[bool, List[str]]:
    hits: List[str] = []
    for p in phrases:
        if p in text:
            hits.append(p)
    return (len(hits) > 0), hits


def assess_healthy_homes_from_text(description: str) -> Dict[str, Any]:
    """
    Extract Healthy Homes-related signals from listing description.

    Returns a dict safe to JSON-store (Analysis.image_analysis attachment).
    """
    text = (description or "").lower()
    if not text.strip():
        return {
            "present": False,
            "confidence": "LOW",
            "claims_compliant": False,
            "signals": {},
            "evidence": [],
            "notes": "No description text provided",
        }

    # Strong explicit claims
    compliant_phrases = [
        "healthy homes compliant",
        "healthy homes compliance",
        "healthy homes standard",
        "healthy homes standards",
        "meets healthy homes",
        "complies with healthy homes",
        "hh compliant",
    ]

    # Heating / insulation / ventilation cues
    heating_phrases = [
        "heat pump",
        "heatpump",
        "ducted heat pump",
        "ducted heating",
        "panel heater",
        "log burner",
        "wood burner",
        "woodburner",
        "fireplace",
    ]
    insulation_phrases = [
        "ceiling insulation",
        "underfloor insulation",
        "floor insulation",
        "insulated ceiling",
        "insulated underfloor",
        "insulated top and bottom",
        "fully insulated",
        "insulation in ceiling",
        "insulation in the ceiling",
        "insulation in the floor",
        "ground moisture barrier",
        "moisture barrier",
        "polythene",
        "polyethylene",
    ]
    ventilation_phrases = [
        "extractor fan",
        "extractor fans",
        "bathroom extractor",
        "kitchen extractor",
        "rangehood",
        "range hood",
        "hrv",
        "dvs",
        "ventilation system",
    ]

    # Risk mentions (often correlate with Healthy Homes remediation)
    damp_phrases = [
        "damp",
        "moisture",
    ]
    mould_phrases = [
        "mould",
        "mold",
        "mildew",
    ]
    condensation_phrases = [
        "condensation",
    ]
    draught_phrases = [
        "draught",
        "draft",
        "draughty",
        "drafty",
    ]

    claims_compliant, compliant_hits = _find_any(text, compliant_phrases)
    has_heating, heating_hits = _find_any(text, heating_phrases)
    has_insulation, insulation_hits = _find_any(text, insulation_phrases)
    has_ventilation, ventilation_hits = _find_any(text, ventilation_phrases)

    mentions_damp, damp_hits = _find_any(text, damp_phrases)
    mentions_mould, mould_hits = _find_any(text, mould_phrases)
    mentions_condensation, cond_hits = _find_any(text, condensation_phrases)
    mentions_draughts, draught_hits = _find_any(text, draught_phrases)

    evidence: List[_Match] = []
    for p in compliant_hits:
        evidence.append(_Match("claims_compliant", p))
    for p in heating_hits:
        evidence.append(_Match("heating", p))
    for p in insulation_hits:
        evidence.append(_Match("insulation", p))
    for p in ventilation_hits:
        evidence.append(_Match("ventilation", p))
    for p in damp_hits:
        evidence.append(_Match("risk_damp", p))
    for p in mould_hits:
        evidence.append(_Match("risk_mould", p))
    for p in cond_hits:
        evidence.append(_Match("risk_condensation", p))
    for p in draught_hits:
        evidence.append(_Match("risk_draughts", p))

    # Confidence heuristic
    if claims_compliant:
        confidence = "HIGH"
    else:
        positives = sum([1 if has_heating else 0, 1 if has_insulation else 0, 1 if has_ventilation else 0])
        confidence = "MEDIUM" if positives >= 2 else "LOW"

    notes: List[str] = []
    if claims_compliant:
        notes.append("Listing explicitly claims Healthy Homes compliance (seller-claimed).")
    if mentions_damp or mentions_mould or mentions_condensation:
        notes.append("Listing mentions damp/mould/condensation (risk signal).")

    return {
        "present": True,
        "confidence": confidence,
        "claims_compliant": claims_compliant,
        "signals": {
            "has_heating": has_heating,
            "has_insulation": has_insulation,
            "has_ventilation": has_ventilation,
            "mentions_damp": mentions_damp,
            "mentions_mould": mentions_mould,
            "mentions_condensation": mentions_condensation,
            "mentions_draughts": mentions_draughts,
        },
        "evidence": [{"key": m.key, "phrase": m.phrase} for m in evidence][:30],
        "notes": " ".join(notes) if notes else "",
    }

