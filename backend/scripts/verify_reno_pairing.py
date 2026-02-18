#!/usr/bin/env python3
"""
Verify Vertex vision output pairs correctly with renovation cost estimation.
Fetches listing, runs vision, runs renovation, traces mapping.
Usage: python scripts/verify_reno_pairing.py <listing_id_or_url>
"""
import json
import re
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))

# Suppress verbose logging
import logging
logging.basicConfig(level=logging.WARNING)
for n in ["urllib3", "httpcore", "httpx", "google", "app"]:
    logging.getLogger(n).setLevel(logging.WARNING)

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/145.0",
    "Referer": "https://www.trademe.co.nz/",
    "Origin": "https://www.trademe.co.nz",
}

def fetch_listing(listing_id: str) -> dict:
    import requests
    url = f"https://api.trademe.co.nz/v1/listings/{listing_id}.json?return_canonical=true&return_variants=true"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    photos = []
    for p in data.get("Photos", []):
        v = p.get("Value", {})
        u = v.get("FullSize") or v.get("Large") or ""
        if u:
            photos.append(u)
    attrs = {a.get("Name"): a.get("Value") for a in data.get("Attributes", []) if a.get("Name")}
    floor_area = None
    if attrs.get("floor_area"):
        m = re.search(r"([\d,.]+)", str(attrs["floor_area"]))
        if m:
            floor_area = float(m.group(1).replace(",", ""))
    bedrooms = None
    if attrs.get("bedrooms"):
        try:
            bedrooms = int(str(attrs["bedrooms"]).split()[0])
        except (ValueError, IndexError):
            bedrooms = 3
    return {
        "listing_id": str(listing_id),
        "photos": photos,
        "floor_area": floor_area,
        "bedrooms": bedrooms or 3,
        "address": data.get("Address", ""),
    }

def extract_listing_id(ident: str) -> str:
    if ident.isdigit():
        return ident
    m = re.search(r"/listing/(\d+)", ident)
    if m:
        return m.group(1)
    m = re.search(r"(\d{7,})", ident)
    if m:
        return m.group(1)
    raise ValueError(f"Cannot extract listing ID from: {ident}")

def main():
    ident = sys.argv[1] if len(sys.argv) > 1 else "5756325957"
    listing_id = extract_listing_id(ident)

    print("=" * 72)
    print("  Vertex -> Renovation Pairing Verification")
    print("=" * 72)
    print(f"\n  Listing: {listing_id}")

    # Fetch listing
    print("\n  Fetching listing...")
    listing = fetch_listing(listing_id)
    print(f"  Photos: {len(listing['photos'])}, floor_area: {listing.get('floor_area')}, bedrooms: {listing.get('bedrooms')}")

    if not listing["photos"]:
        print("  No photos.")
        return 1

    # Run vision (limit to 4 for speed)
    from app.services.external.vision_api import VisionAPIClient
    client = VisionAPIClient()
    image_analysis = client.analyze_listing_photos(listing["photos"][:4])

    print("\n" + "-" * 72)
    print("  VERTEX OUTPUT (image_analysis)")
    print("-" * 72)
    for k in ["overall_reno_level", "roof_condition", "exterior_condition", "interior_quality",
              "structural_concerns", "key_renovation_items", "confidence"]:
        v = image_analysis.get(k)
        if v is not None:
            print(f"    {k}: {json.dumps(v)[:120]}{'...' if len(json.dumps(v)) > 120 else ''}")

    # Build listing_data for renovation
    listing_data = {
        "floor_area": listing.get("floor_area"),
        "bedrooms": listing.get("bedrooms", 3),
        "land_area": None,
    }

    # Run renovation estimation
    from app.services.analysis.renovation import (
        estimate_renovation_cost,
        COSTS_PER_SQM,
        RENOVATION_ITEMS,
    )
    renovation = estimate_renovation_cost(listing_data, image_analysis)

    print("\n" + "-" * 72)
    print("  RENOVATION COST ESTIMATE (from estimate_renovation_cost)")
    print("-" * 72)
    print(json.dumps(renovation, indent=2))

    print("\n" + "=" * 72)
    print("  PAIRING VERIFICATION")
    print("=" * 72)

    reno_level = image_analysis.get("overall_reno_level", "MODERATE")
    floor_area = renovation["floor_area_used"]
    cost_per_sqm = COSTS_PER_SQM.get(reno_level, COSTS_PER_SQM["MODERATE"])
    expected_base = floor_area * cost_per_sqm

    print(f"\n  1. overall_reno_level = '{reno_level}'")
    print(f"     -> COSTS_PER_SQM['{reno_level}'] = ${cost_per_sqm}/sqm")
    print(f"     -> base_cost = floor_area ({floor_area}) × {cost_per_sqm} = ${expected_base:,.0f}")
    print(f"     -> ACTUAL base_renovation: ${renovation['base_renovation']:,.0f}")
    match = abs(renovation["base_renovation"] - expected_base) < 1
    print(f"     -> MATCH: {'YES' if match else 'NO'}")

    roof = image_analysis.get("roof_condition")
    print(f"\n  2. roof_condition = '{roof}'")
    if roof == "NEEDS_REPLACE":
        print(f"     -> Adds roof replacement cost (roof_area × $80/sqm)")
    else:
        print(f"     -> No roof add-on (only triggers when NEEDS_REPLACE)")
    print(f"     -> additional_items: {renovation['additional_details']}")

    struct = image_analysis.get("structural_concerns", [])
    struct_str = str(struct).lower()
    print(f"\n  3. structural_concerns = {json.dumps(struct)[:200]}...")
    print(f"     -> Renovation.py checks: 'weatherboard rot'|'weatherboard_rot', 'foundation', 'moisture_damage'")
    wb_match = "weatherboard_rot" in struct or "weatherboard rot" in struct_str
    fnd_match = "foundation_issues" in struct or "foundation" in struct_str
    moist_match = "moisture_damage" in struct_str
    print(f"     -> weatherboard: {wb_match} | foundation: {fnd_match} | moisture_damage: {moist_match}")
    for c in struct:
        cstr = str(c).lower()
        matched = []
        if "weatherboard_rot" in struct or "weatherboard rot" in cstr:
            matched.append("weatherboard+15k")
        if "foundation" in cstr:
            matched.append("foundation+30k")
        if "moisture_damage" in cstr:
            matched.append("moisture+10k")
        status = ", ".join(matched) if matched else "NO MATCH"
        print(f"       '{str(c)[:55]}...' -> {status}")

    key_items = image_analysis.get("key_renovation_items", [])
    print(f"\n  4. key_renovation_items from Vertex: {len(key_items)} items")
    print(f"     -> Used directly as key_items (no fallback to RENOVATION_ITEMS)")
    print(f"     -> First 3: {key_items[:3]}")

    print("\n  Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
