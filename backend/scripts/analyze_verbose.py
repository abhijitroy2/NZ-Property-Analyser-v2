#!/usr/bin/env python3
"""
Verbose Analyze Test Harness.

Runs the full analysis pipeline on a single listing already in the database.
Prints every input/output at each step so you can trace how conclusions were reached.

Usage (from backend/ or project root):
  python scripts/analyze_verbose.py <listing_id_or_url>
  python scripts/analyze_verbose.py --list          # List all listings in DB
  python scripts/analyze_verbose.py 12345678       # By TradeMe listing_id
  python scripts/analyze_verbose.py "https://..."  # By property URL
  python scripts/analyze_verbose.py --no-save 123  # Dry run, don't save to DB

Examples:
  python scripts/analyze_verbose.py --list
  python scripts/analyze_verbose.py 4567890123
  python scripts/analyze_verbose.py --no-save 4567890123
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Windows console encoding fix for Unicode in listing data
def safe_str(s, maxlen=80):
    """Replace non-ASCII chars to avoid cp1252 encode errors on Windows."""
    if s is None:
        return "N/A"
    return str(s)[:maxlen].encode("ascii", "replace").decode("ascii")

# Add backend to path
backend = Path(__file__).resolve().parent.parent
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))

# Enable verbose logging before any app imports
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logging.getLogger("app").setLevel(logging.DEBUG)


def section(title: str, char: str = "="):
    """Print a section header."""
    width = 72
    print()
    print(char * width)
    print(f"  {title}")
    print(char * width)


def subsection(title: str):
    print(f"\n  --- {title} ---")


def pjson(obj, indent: int = 2):
    """Pretty-print JSON-serializable object. Sanitizes for Windows console."""
    s = json.dumps(obj, indent=indent, default=str, ensure_ascii=True)
    return s


def main():
    parser = argparse.ArgumentParser(description="Verbose analysis harness for a single listing")
    parser.add_argument("identifier", nargs="?", help="Listing ID, DB id, or TradeMe URL")
    parser.add_argument("--list", action="store_true", help="List all listings in database")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to DB (dry run)")
    args = parser.parse_args()

    from app.database import init_db, SessionLocal
    from app.models.listing import Listing
    from app.models.analysis import Analysis

    init_db()
    db = SessionLocal()

    try:
        if args.list:
            listings = db.query(Listing).order_by(Listing.id.desc()).limit(50).all()
            print(f"\nFound {len(listings)} listings (most recent 50):\n")
            for L in listings:
                print(f"  id={L.id:6}  listing_id={L.listing_id:12}  {L.address or L.suburb or 'N/A'}")
                print(f"            {safe_str(L.display_price, 20):20}  {safe_str(L.property_url, 60)}...")
            return 0

        if not args.identifier:
            parser.print_help()
            print("\nRun with --list to see available listings.")
            return 1

        # Find listing
        ident = args.identifier.strip()
        listing = None

        # Try by listing_id (TradeMe ID)
        if ident.isdigit():
            listing = db.query(Listing).filter(Listing.listing_id == ident).first()
            if listing:
                print(f"Matched by listing_id: {ident}")

        # Try by DB id
        if not listing and ident.isdigit():
            listing = db.query(Listing).filter(Listing.id == int(ident)).first()
            if listing:
                print(f"Matched by DB id: {ident}")

        # Try by URL (property_url contains)
        if not listing:
            listing = db.query(Listing).filter(Listing.property_url.contains(ident)).first()
            if listing:
                print(f"Matched by property_url containing: {ident[:50]}...")

        # Try extracting ID from URL
        if not listing:
            match = re.search(r"/(\d{6,})", ident)
            if match:
                lid = match.group(1)
                listing = db.query(Listing).filter(Listing.listing_id == lid).first()
                if listing:
                    print(f"Matched by listing_id extracted from URL: {lid}")

        if not listing:
            print(f"ERROR: No listing found for: {args.identifier}")
            print("Run with --list to see available listings.")
            return 1

        section("LISTING INPUT", "=")
        print(f"  DB id:       {listing.id}")
        print(f"  listing_id:  {listing.listing_id}")
        print(f"  address:     {listing.address} / {listing.full_address}")
        print(f"  suburb:      {listing.suburb}, {listing.district}, {listing.region}")
        print(f"  bedrooms:    {listing.bedrooms}, bathrooms: {listing.bathrooms}")
        print(f"  land_area:   {listing.land_area} m², floor_area: {listing.floor_area} m²")
        print(f"  display_price: {listing.display_price}")
        print(f"  asking_price:  {listing.asking_price}")
        print(f"  capital_value: {listing.capital_value}")
        print(f"  title_type:  {listing.title_type}")
        print(f"  property_type: {listing.property_type}")
        print(f"  property_url: {listing.property_url}")
        print(f"  photos:      {len(listing.photos or [])} URLs")
        print(f"  nearby_properties: {len(listing.nearby_properties or [])} comparables")
        print(f"  estimated_market_price: {listing.estimated_market_price}")
        print(f"  estimated_weekly_rent:  {listing.estimated_weekly_rent}")

        # Run analysis with verbose output
        from app.services.pipeline import PropertyPipeline
        from app.services.filters.price_filter import filter_price
        from app.services.filters.title_filter import filter_title
        from app.services.filters.population_filter import filter_population
        from app.services.filters.property_type_filter import filter_property_type
        from app.services.analysis.insurance import check_insurability
        from app.services.analysis.renovation import estimate_renovation_cost
        from app.services.analysis.timeline import estimate_timeline
        from app.services.analysis.arv import estimate_arv
        from app.services.analysis.rental import estimate_rental_income
        from app.services.external.council_api import CouncilAPIClient
        from app.services.external.vision_api import VisionAPIClient
        from app.services.financial.flip_model import calculate_flip_financials
        from app.services.financial.rental_model import calculate_rental_financials
        from app.services.financial.strategy import decide_strategy
        from app.services.scoring.scorer import calculate_composite_score, WEIGHTS

        pipeline = PropertyPipeline(db)
        listing_data = pipeline._listing_to_dict(listing)

        # ========== STAGE 1: FILTERS ==========
        section("STAGE 1: HARD FILTERS")
        section("", "-")

        subsection("Price Filter")
        print("  Config: MAX_PRICE from settings")
        status, reason = filter_price(listing)
        print(f"  Input:  asking_price={listing.asking_price}, capital_value={listing.capital_value}")
        print(f"  Output: {status} - {reason or 'Passed'}")
        if status == "REJECT":
            print("\n  >>> LISTING REJECTED - stopping here")
            return 0

        subsection("Title Type Filter")
        print(f"  Input:  title_type={listing.title_type!r}, description length={len(listing.description or '')}")
        status, reason = filter_title(listing)
        print(f"  Output: {status} - {reason or 'Passed'}")
        if status == "REJECT":
            print("\n  >>> LISTING REJECTED - stopping here")
            return 0

        subsection("Population Filter")
        status, reason, population_data = filter_population(listing)
        print(f"  Input:  suburb={listing.suburb}, district={listing.district}, region={listing.region}")
        print(f"  Output: {status} - {reason or 'Passed'}")
        print(f"  Population data:\n{pjson(population_data, 4)}")
        if status == "REJECT":
            print("\n  >>> LISTING REJECTED - stopping here")
            return 0

        subsection("Demand Profile (property type)")
        _, _, demand_profile = filter_property_type(listing)
        print(f"  Input:  property_type={listing.property_type}")
        print(f"  Output:\n{pjson(demand_profile, 4)}")

        # ========== STAGE 2: DEEP ANALYSIS ==========
        section("STAGE 2: DEEP ANALYSIS")
        section("", "-")

        subsection("Insurability")
        insurability = check_insurability(listing_data)
        print(f"  Input:  listing_data (address, region, etc.)")
        print(f"  Output:\n{pjson(insurability, 4)}")

        subsection("Vision API (image analysis)")
        image_analysis = pipeline.vision_client.analyze_listing_photos(listing.photos or [])
        print(f"  Input:  {len(listing.photos or [])} photo URLs")
        print(f"  Output:\n{pjson(image_analysis, 4)}")

        subsection("Renovation Estimate")
        renovation = estimate_renovation_cost(listing_data, image_analysis)
        print(f"  Input:  listing_data + image_analysis.overall_reno_level, key_renovation_items")
        print(f"  Output:\n{pjson(renovation, 4)}")

        subsection("Timeline Estimate")
        timeline = estimate_timeline(renovation)
        print(f"  Input:  renovation (level, total_estimated)")
        print(f"  Output:\n{pjson(timeline, 4)}")

        subsection("ARV (After Repair Value)")
        arv = estimate_arv(
            listing_data,
            listing.nearby_properties or [],
            listing.estimated_market_price or "",
        )
        print(f"  Input:  nearby_properties={len(listing.nearby_properties or [])}, est_market={listing.estimated_market_price}")
        print(f"  Output:\n{pjson(arv, 4)}")

        subsection("Rental Income Estimate")
        rental_income = estimate_rental_income(
            listing_data,
            listing.estimated_weekly_rent or "",
        )
        print(f"  Input:  estimated_weekly_rent={listing.estimated_weekly_rent}")
        print(f"  Output:\n{pjson(rental_income, 4)}")

        subsection("Council Rates")
        council_rates = pipeline.council_client.get_council_rates(
            listing.address or "", listing.district or "",
        )
        print(f"  Input:  address, district")
        print(f"  Output:\n{pjson(council_rates, 4)}")

        subsection("Subdivision Potential")
        from app.services.analysis.subdivision import analyze_subdivision_potential
        subdivision = analyze_subdivision_potential(listing_data)
        print(f"  Input:  land_area={listing.land_area}, asking_price, district, region")
        print(f"  Output:\n{pjson(subdivision, 4)}")

        # Build full analysis_results for stage 3
        analysis_results = {
            "population": population_data,
            "demand_profile": demand_profile,
            "insurability": insurability,
            "image_analysis": image_analysis,
            "renovation": renovation,
            "timeline": timeline,
            "arv": arv,
            "rental_income": rental_income,
            "council_rates": council_rates,
            "subdivision": subdivision,
        }

        # ========== STAGE 3: FINANCIALS ==========
        section("STAGE 3: FINANCIAL MODELS")
        section("", "-")

        financial_results = pipeline._run_stage3_financials(listing, analysis_results)
        flip = financial_results["flip"]
        rental = financial_results["rental"]
        strategy = financial_results["strategy"]

        subsection("Flip Model")
        print(f"  Input:  purchase={listing.asking_price or 0}, reno={renovation.get('total_estimated')}, arv, timeline")
        print(f"  Output:\n{pjson(flip, 4)}")

        subsection("Rental Model")
        print(f"  Output:\n{pjson(rental, 4)}")

        subsection("Strategy Decision")
        print(f"  Output:\n{pjson(strategy, 4)}")

        # ========== SCORING ==========
        section("SCORING")
        section("", "-")

        scoring_data = {
            "strategy_decision": strategy,
            "flip": flip,
            "rental": rental,
            "timeline": analysis_results["timeline"],
            "arv": analysis_results["arv"],
            "rental_estimate": analysis_results["rental_income"],
            "subdivision": analysis_results["subdivision"],
            "population": analysis_results["population"],
            "insurability": analysis_results["insurability"],
            "image_analysis": analysis_results["image_analysis"],
        }
        score_result = calculate_composite_score(scoring_data)

        subsection("Weights")
        print(pjson(WEIGHTS, 4))

        subsection("Component Scores")
        WEIGHT_MAP = {"roi_score": "roi", "timeline_score": "timeline", "confidence_score": "confidence",
                      "subdivision_score": "subdivision", "location_score": "location_growth", "insurability_score": "insurability"}
        for k, v in (score_result.get("component_scores") or {}).items():
            w_key = WEIGHT_MAP.get(k, k)
            pct = (WEIGHTS.get(w_key) or 0) * 100
            print(f"    {k}: {v:.1f}  (weight {pct:.0f}%)")

        subsection("Composite Score & Verdict")
        print(f"  composite_score: {score_result.get('composite_score')}")
        print(f"  verdict:         {score_result.get('verdict')}")
        print(f"  confidence_level: {score_result.get('confidence_level')}")
        print(f"  flags:           {score_result.get('flags')}")
        print(f"  next_steps:      {score_result.get('next_steps')}")

        # Save to DB unless --no-save
        if not args.no_save:
            section("SAVING TO DATABASE")
            pipeline._store_analysis(listing, analysis_results, financial_results, score_result)
            listing.filter_status = "passed"
            listing.analysis_status = "completed"
            db.commit()
            print("  Analysis saved to database.")
        else:
            print("\n  [--no-save] Skipped saving to database.")

        section("DONE", "=")
        return 0

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
