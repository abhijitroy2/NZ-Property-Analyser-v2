#!/usr/bin/env python3
"""
Run full pipeline with verbose Vertex -> Renovation tracing.
Dumps human-readable log to backend/logs/pipeline_vertex_reno_<timestamp>.log

Usage:
  python scripts/run_pipeline_vertex_trace.py              # Full pipeline (scrape + analyze)
  python scripts/run_pipeline_vertex_trace.py --analyze-only  # Only analyze pending (no scrape)
  python scripts/run_pipeline_vertex_trace.py --reset         # Reset analyses to pending first
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))

# Quiet console
logging.basicConfig(level=logging.WARNING)
for n in ["urllib3", "httpcore", "httpx", "google", "app", "sqlalchemy"]:
    logging.getLogger(n).setLevel(logging.WARNING)

LOG_DIR = backend / "logs"
LOG_DIR.mkdir(exist_ok=True)


def _trace_vertex_to_reno(log: object, image_analysis: dict, renovation: dict, listing_data: dict) -> None:
    """Write pairing trace to log."""
    reno_level = image_analysis.get("overall_reno_level", "?")
    roof = image_analysis.get("roof_condition", "?")
    struct = image_analysis.get("structural_concerns", [])
    struct_str = str(struct).lower()
    floor = renovation.get("floor_area_used", 0)
    base = renovation.get("base_renovation", 0)
    add = renovation.get("additional_items", 0)
    total = renovation.get("total_estimated", 0)

    log.write("    PAIRING TRACE:\n")
    log.write(f"      overall_reno_level={reno_level} -> base ${base:,.0f} (floor={floor}m2)\n")
    log.write(f"      roof_condition={roof} -> add_on=${add:,.0f} ({renovation.get('additional_details', [])})\n")
    wb = "weatherboard_rot" in struct or "weatherboard rot" in struct_str
    fnd = "foundation_issues" in struct or "foundation" in struct_str
    fnd_shed = fnd and ("shed" in struct_str or "outbuilding" in struct_str)
    moist = "moisture_damage" in struct_str
    log.write(f"      structural_concerns: weatherboard={wb} foundation={fnd} (shed={fnd_shed}) moisture={moist}\n")
    log.write(f"      total_estimated=${total:,.0f}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze pending, skip scrape")
    parser.add_argument("--reset", action="store_true", help="Reset all analyses to pending before run")
    args = parser.parse_args()

    from app.database import init_db, SessionLocal
    from app.models.listing import Listing
    from app.services.pipeline import PropertyPipeline
    from app.services.analysis.renovation import estimate_renovation_cost

    init_db()
    db = SessionLocal()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"pipeline_vertex_reno_{timestamp}.log"
    log_file = open(log_path, "w", encoding="utf-8")

    def log(msg: str) -> None:
        log_file.write(msg + "\n")
        log_file.flush()

    try:
        log("=" * 80)
        log("  PIPELINE RUN WITH VERTEX -> RENOVATION VERBOSE TRACE")
        log(f"  Started: {datetime.now().isoformat()}")
        log(f"  Log file: {log_path}")
        log("=" * 80)

        if args.reset:
            log("\n  Resetting all analyses to pending...")
            updated = db.query(Listing).filter(Listing.analysis_status.in_(["completed", "in_progress"])).update(
                {"analysis_status": "pending", "filter_status": "pending", "filter_rejection_reason": None},
                synchronize_session=False,
            )
            db.commit()
            log(f"  Reset {updated} listings to pending.")

        # Run pipeline with tracing
        pipeline = PropertyPipeline(db)

        if not args.analyze_only:
            log("\n" + "-" * 80)
            log("  PHASE 1: SCRAPE")
            log("-" * 80)
            try:
                pipeline.scrape_new_listings()
                total = db.query(Listing).count()
                log(f"  Listings in DB: {total}")
            except Exception as e:
                log(f"  Scrape error: {e}")

        log("\n" + "-" * 80)
        log("  PHASE 2: FILTER + ANALYZE (with Vertex -> Reno trace)")
        log("-" * 80)

        pending = db.query(Listing).filter(Listing.analysis_status.in_(["pending", "failed"])).all()
        log(f"\n  Pending listings: {len(pending)}")

        for i, listing in enumerate(pending, 1):
            log("\n" + "=" * 80)
            log(f"  LISTING {i}/{len(pending)}: {listing.listing_id} | {listing.address or 'N/A'}")
            log("=" * 80)

            try:
                # Stage 1 filters
                passed, reason = pipeline._run_stage1_filters(listing)
                if not passed:
                    log(f"  REJECTED (filters): {reason}")
                    listing.filter_status = "rejected"
                    listing.filter_rejection_reason = reason
                    listing.analysis_status = "completed"
                    db.commit()
                    continue

                listing.filter_status = "passed"
                db.commit()

                # Stage 2 with tracing
                listing_data = pipeline._listing_to_dict(listing)
                from app.services.filters.population_filter import filter_population
                from app.services.filters.property_type_filter import filter_property_type
                _, _, population_data = filter_population(listing)
                _, _, demand_profile = filter_property_type(listing)

                log(f"  Photos: {len(listing.photos or [])} | floor_area: {listing_data.get('floor_area')} | bedrooms: {listing_data.get('bedrooms')}")

                # Vision
                log("  --- VERTEX OUTPUT (image_analysis) ---")
                image_analysis = pipeline.vision_client.analyze_listing_photos(listing.photos or [])
                for k in ["overall_reno_level", "roof_condition", "exterior_condition", "interior_quality",
                          "structural_concerns", "key_renovation_items", "confidence", "source"]:
                    v = image_analysis.get(k)
                    if v is not None:
                        s = json.dumps(v) if not isinstance(v, (list, dict)) else json.dumps(v)[:200]
                        log(f"    {k}: {s}")

                # Renovation
                log("  --- RENOVATION (estimate_renovation_cost) ---")
                renovation = estimate_renovation_cost(listing_data, image_analysis)
                log(f"    {json.dumps(renovation, indent=6)}".replace("\n", "\n    "))

                _trace_vertex_to_reno(log_file, image_analysis, renovation, listing_data)

                # Rest of Stage 2 + Stage 3 + scoring + store
                from app.services.analysis.insurance import check_insurability
                from app.services.analysis.timeline import estimate_timeline
                from app.services.analysis.arv import estimate_arv
                from app.services.analysis.rental import estimate_rental_income
                from app.services.external.council_api import CouncilAPIClient
                from app.services.analysis.subdivision import analyze_subdivision_potential
                from app.services.financial.flip_model import calculate_flip_financials
                from app.services.financial.rental_model import calculate_rental_financials
                from app.services.financial.strategy import decide_strategy
                from app.services.scoring.scorer import calculate_composite_score

                insurability = check_insurability(listing_data)
                timeline = estimate_timeline(renovation)
                arv = estimate_arv(listing_data, listing.nearby_properties or [], listing.estimated_market_price or "")
                rental_income = estimate_rental_income(listing_data, listing.estimated_weekly_rent or "")
                council_rates = pipeline.council_client.get_council_rates(listing.address or "", listing.district or "")
                subdivision = analyze_subdivision_potential(listing_data)

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

                analysis_for_financial = {
                    "renovation": renovation,
                    "arv": arv,
                    "rental": rental_income,
                    "council": council_rates,
                    "insurability": insurability,
                    "timeline": timeline,
                }

                from app.services.filters.price_filter import get_effective_asking_price
                effective_price = get_effective_asking_price(listing) or 0
                listing_dict = {"price_display": effective_price, "bedrooms": listing.bedrooms or 3}
                flip = calculate_flip_financials(listing_dict, analysis_for_financial)
                rental = calculate_rental_financials(listing_dict, analysis_for_financial)
                strategy = decide_strategy(flip, rental, subdivision)

                scoring_data = {
                    "strategy_decision": strategy,
                    "flip": flip,
                    "rental": rental,
                    "timeline": timeline,
                    "arv": arv,
                    "rental_estimate": rental_income,
                    "subdivision": subdivision,
                    "population": population_data,
                    "insurability": insurability,
                    "image_analysis": image_analysis,
                }
                score_result = calculate_composite_score(scoring_data)

                pipeline._store_analysis(listing, analysis_results, {"flip": flip, "rental": rental, "strategy": strategy}, score_result)
                listing.filter_status = "passed"
                listing.analysis_status = "completed"
                db.commit()

                log(f"  RESULT: score={score_result.get('composite_score')} verdict={score_result.get('verdict')}")

            except Exception as e:
                log(f"  ERROR: {e}")
                import traceback
                log(traceback.format_exc())
                listing.analysis_status = "failed"
                db.commit()

        # Re-rank
        log("\n" + "-" * 80)
        log("  PHASE 3: RE-RANK")
        log("-" * 80)
        from app.models.analysis import Analysis
        analyses = db.query(Analysis).filter(Analysis.composite_score.isnot(None)).order_by(Analysis.composite_score.desc()).all()
        for i, a in enumerate(analyses, 1):
            a.rank = i
        db.commit()
        log(f"  Re-ranked {len(analyses)} listings.")

        log("\n" + "=" * 80)
        log("  PIPELINE COMPLETE")
        log("=" * 80)
        log(f"  Log saved to: {log_path}")
        print(f"\nPipeline complete. Log: {log_path}")

    except Exception as e:
        log(f"\nPipeline error: {e}")
        import traceback
        log(traceback.format_exc())
        raise
    finally:
        log_file.close()
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
