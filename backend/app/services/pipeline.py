"""
Property Processing Pipeline.
Orchestrates the full data pipeline: scrape -> filter -> analyze -> score.
"""

import copy
import hashlib
import json
import logging
import time
from typing import List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.analysis import Analysis
from app.models.listing import Listing

from app.services.scraper.trademe import TradeMeScraper
from app.services.filters.price_filter import filter_price, get_effective_asking_price
from app.services.filters.title_filter import filter_title
from app.services.filters.population_filter import filter_population
from app.services.filters.property_type_filter import filter_property_type

from app.services.analysis.insurance import check_insurability
from app.services.analysis.renovation import estimate_renovation_cost
from app.services.analysis.timeline import estimate_timeline
from app.services.analysis.arv import estimate_arv
from app.services.analysis.rental import estimate_rental_income
from app.services.analysis.subdivision import analyze_subdivision_potential
from app.services.analysis.healthy_homes_text import assess_healthy_homes_from_text
from app.services.external.council_api import CouncilAPIClient
from app.services.external.vision_api import VisionAPIClient, vision_has_valid_reno_timeline

from app.services.financial.flip_model import calculate_flip_financials
from app.services.financial.rental_model import calculate_rental_financials
from app.services.financial.strategy import decide_strategy

from app.services.scoring.scorer import calculate_composite_score
from app.pipeline_status import set_running, update_progress, set_idle

logger = logging.getLogger(__name__)


def _compute_photos_hash(photos: List[str]) -> str:
    """Compute deterministic hash of photo URLs for cache invalidation."""
    urls = (photos or [])[:6]  # Match vision API limit
    return hashlib.sha256(json.dumps(sorted(urls), sort_keys=True).encode()).hexdigest()


def _compute_subdivision_input_hash(listing_data: dict) -> str:
    """Compute hash of subdivision inputs for cache invalidation."""
    key = {
        "address": listing_data.get("address", ""),
        "district": listing_data.get("district", ""),
        "region": listing_data.get("region", ""),
        "land_area": listing_data.get("land_area"),
    }
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()


def _timeline_notes(weeks: int) -> str:
    """Human-readable timeline notes for openai_deep mode."""
    if weeks == 0:
        return "No renovation required"
    if weeks <= 4:
        return "Quick turnaround - cosmetic work only"
    if weeks <= 8:
        return "Within 8-week target - manageable renovation"
    if weeks <= 12:
        return "Exceeds 8-week target - moderate complexity"
    if weeks <= 16:
        return "Significant renovation - plan for extended holding costs"
    return "Major renovation - consider phased approach or adjust expectations"


class PropertyPipeline:
    """Orchestrates the full property evaluation pipeline."""

    def __init__(self, db: Session):
        self.db = db
        self.scraper = TradeMeScraper(db)
        self.council_client = CouncilAPIClient()
        self.vision_client = VisionAPIClient()

    def run_full_pipeline(self):
        """Run the complete pipeline: scrape, filter, analyze, score."""
        logger.info("=== Starting full pipeline ===")
        try:
            set_running("full", "Starting full pipeline...")
            # Step 1: Scrape new listings
            self.scrape_new_listings()

            # Step 2: Filter and analyze
            self.analyze_pending_listings()

            # Step 3: Re-rank all analyzed listings
            set_running("full", "Re-ranking listings...")
            self._rerank_all()

            logger.info("=== Pipeline complete ===")
        finally:
            set_idle()

    def scrape_new_listings(self):
        """Pull new listings from TradeMe. Reads URLs from DB, falls back to .env."""
        from app.api.settings import get_active_search_urls, _sync_to_scraper_input
        from app.models.search_url import SearchURL

        search_urls = get_active_search_urls(self.db)
        if not search_urls:
            logger.warning("No search URLs configured. Add URLs in Settings or set TRADEME_SEARCH_URLS in .env")
            return

        set_running("scrape", f"Scraping {len(search_urls)} search URL(s)...", {"current": 0, "total": len(search_urls)})

        # Sync enabled URLs to TM-scraper-1 input.txt before scraping
        db_urls = self.db.query(SearchURL).filter(SearchURL.enabled == True).all()
        if db_urls:
            _sync_to_scraper_input(db_urls)

        total_new = 0
        for i, url in enumerate(search_urls):
            update_progress(f"Scraping URL {i + 1} of {len(search_urls)}", i + 1, len(search_urls))
            try:
                new_listings = self.scraper.scrape_search_url(url)
                total_new += len(new_listings)
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")

        logger.info(f"Scraped {total_new} total listings")

    def analyze_pending_listings(self):
        """Run analysis on all pending/unanalyzed listings."""
        pending = (
            self.db.query(Listing)
            .filter(Listing.analysis_status.in_(["pending", "failed"]))
            .all()
        )

        logger.info(f"Analyzing {len(pending)} pending listings")

        if pending:
            set_running("analyze", f"Analyzing {len(pending)} listing(s)...", {"current": 0, "total": len(pending)})
        try:
            for i, listing in enumerate(pending):
                update_progress(f"Analyzing: {listing.address or listing.listing_id}", i + 1, len(pending))
                try:
                    self.analyze_listing(listing)
                except Exception as e:
                    logger.error(f"Failed to analyze listing {listing.listing_id}: {e}")
                    listing.analysis_status = "failed"
                    self.db.commit()

                # Rate limit: wait between listings when using OpenAI vision (avoids 200k TPM)
                if (
                    settings.vision_provider == "openai"
                    and listing.filter_status == "passed"
                    and i < len(pending) - 1
                ):
                    delay = getattr(settings, "vision_rate_limit_delay_seconds", 65)
                    if delay > 0:
                        logger.info(f"Rate limit: waiting {delay}s before next listing")
                        time.sleep(delay)
        finally:
            if pending:
                # Don't call set_idle here - run_full_pipeline will do it, or standalone analyze will
                pass

    def analyze_listing(self, listing: Listing):
        """Run full analysis on a single listing."""
        logger.info(f"Analyzing listing {listing.listing_id}: {listing.address}")
        listing.analysis_status = "in_progress"
        self.db.commit()

        # === STAGE 1: Hard Filters ===
        passed, rejection_reason = self._run_stage1_filters(listing)

        if not passed:
            listing.filter_status = "rejected"
            listing.filter_rejection_reason = rejection_reason
            listing.analysis_status = "completed"
            self.db.commit()
            logger.info(f"Listing {listing.listing_id} rejected: {rejection_reason}")
            return

        listing.filter_status = "passed"
        self.db.commit()

        # === STAGE 2: Deep Analysis ===
        analysis_results = self._run_stage2_analysis(listing)

        # === STAGE 3: Financial Modeling ===
        financial_results = self._run_stage3_financials(listing, analysis_results)

        # === SCORING ===
        scoring_data = {
            "strategy_decision": financial_results["strategy"],
            "flip": financial_results["flip"],
            "rental": financial_results["rental"],
            "timeline": analysis_results["timeline"],
            "arv": analysis_results["arv"],
            "rental_estimate": analysis_results["rental_income"],
            "subdivision": analysis_results["subdivision"],
            "population": analysis_results["population"],
            "insurability": analysis_results["insurability"],
            "image_analysis": analysis_results["image_analysis"],
        }

        score_result = calculate_composite_score(scoring_data)

        # Store analysis
        self._store_analysis(listing, analysis_results, financial_results, score_result)

        listing.analysis_status = "completed"
        self.db.commit()

        logger.info(
            f"Listing {listing.listing_id}: Score={score_result['composite_score']}, "
            f"Verdict={score_result['verdict']}, "
            f"Strategy={financial_results['strategy'].get('recommended_strategy')}"
        )

    def _run_stage1_filters(self, listing: Listing) -> tuple:
        """Run Stage 1 hard filters. Returns (passed: bool, reason: str)."""
        # Price filter
        status, reason = filter_price(listing)
        if status == "REJECT":
            return False, reason

        # Title type filter
        status, reason = filter_title(listing)
        if status == "REJECT":
            return False, reason

        # Population filter
        status, reason, _ = filter_population(listing)
        if status == "REJECT":
            return False, reason

        return True, ""

    def _run_stage2_analysis(self, listing: Listing) -> dict:
        """Run Stage 2 deep analysis. Returns dict of all analysis results."""
        listing_data = self._listing_to_dict(listing)

        # Population data (already partially done in filters)
        _, _, population_data = filter_population(listing)

        # Demand profile
        _, _, demand_profile = filter_property_type(listing)

        # Insurability
        insurability = check_insurability(listing_data)

        # Image analysis: reuse cached OpenAI/vision result when photos unchanged
        photos_hash = _compute_photos_hash(listing.photos or [])
        existing_analysis = self.db.query(Analysis).filter(Analysis.listing_id == listing.id).first()
        if (
            existing_analysis
            and existing_analysis.image_analysis
            and getattr(existing_analysis, "vision_photos_hash", None) == photos_hash
        ):
            image_analysis = copy.deepcopy(existing_analysis.image_analysis)
            logger.info(f"Listing {listing.listing_id}: reusing cached vision (photos unchanged)")
        else:
            image_analysis = self.vision_client.analyze_listing_photos(listing.photos or [])

        # Healthy Homes (seller-claimed) signals from listing description
        # Stored alongside image analysis so downstream (reno estimate) can consider it
        hh_text = assess_healthy_homes_from_text(listing.description or "")
        try:
            if isinstance(image_analysis, dict):
                image_analysis["healthy_homes_text"] = hh_text
        except Exception:
            # Never break the pipeline for enrichment data
            pass

        # Renovation estimate and timeline: fork by analysis_mode
        if (
            settings.analysis_mode == "openai_deep"
            and vision_has_valid_reno_timeline(image_analysis)
        ):
            cost = image_analysis.get("estimated_renovation_cost_nzd", 0)
            weeks = image_analysis.get("estimated_timeline_weeks", 8)
            renovation = {
                "total_estimated": round(float(cost), 0),
                "renovation_level": image_analysis.get("overall_reno_level", "MODERATE"),
                "source": "openai_vision",
                "key_items": image_analysis.get("key_renovation_items", []),
            }
            timeline = {
                "estimated_weeks": int(weeks),
                "within_8_week_target": int(weeks) <= 8,
                "renovation_level": image_analysis.get("overall_reno_level", "MODERATE"),
                "notes": _timeline_notes(int(weeks)),
                "source": "openai_vision",
            }
        else:
            renovation = estimate_renovation_cost(listing_data, image_analysis)
            timeline = estimate_timeline(renovation)

        # ARV
        arv = estimate_arv(
            listing_data,
            listing.nearby_properties or [],
            listing.estimated_market_price or "",
        )

        # Rental income
        rental_income = estimate_rental_income(
            listing_data,
            listing.estimated_weekly_rent or "",
        )

        # Council rates
        council_rates = self.council_client.get_council_rates(
            listing.address or "",
            listing.district or "",
        )

        # Subdivision potential: reuse cached result when location/land unchanged (saves geocoding + zone API)
        subdiv_hash = _compute_subdivision_input_hash(listing_data)
        if (
            existing_analysis
            and existing_analysis.subdivision_analysis
            and getattr(existing_analysis, "subdivision_input_hash", None) == subdiv_hash
        ):
            subdivision = copy.deepcopy(existing_analysis.subdivision_analysis)
            logger.info(f"Listing {listing.listing_id}: reusing cached subdivision analysis")
        else:
            subdivision = analyze_subdivision_potential(listing_data)

        return {
            "population": population_data,
            "demand_profile": demand_profile,
            "insurability": insurability,
            "image_analysis": image_analysis,
            "vision_photos_hash": photos_hash,
            "renovation": renovation,
            "timeline": timeline,
            "arv": arv,
            "rental_income": rental_income,
            "council_rates": council_rates,
            "subdivision": subdivision,
            "subdivision_input_hash": subdiv_hash,
        }

    def _run_stage3_financials(self, listing: Listing, analysis: dict) -> dict:
        """Run Stage 3 financial models."""
        effective_price = get_effective_asking_price(listing) or 0
        listing_dict = {
            "price_display": effective_price,
            "bedrooms": listing.bedrooms or 3,
        }

        analysis_for_financial = {
            "renovation": analysis["renovation"],
            "arv": analysis["arv"],
            "rental": analysis["rental_income"],
            "council": analysis["council_rates"],
            "insurability": analysis["insurability"],
            "timeline": analysis["timeline"],
        }

        flip = calculate_flip_financials(listing_dict, analysis_for_financial)
        rental = calculate_rental_financials(listing_dict, analysis_for_financial)
        strategy = decide_strategy(flip, rental, analysis["subdivision"])

        return {
            "flip": flip,
            "rental": rental,
            "strategy": strategy,
        }

    def _store_analysis(self, listing: Listing, analysis: dict, financials: dict, scoring: dict):
        """Store analysis results in database."""
        # Check if analysis already exists
        existing = self.db.query(Analysis).filter(Analysis.listing_id == listing.id).first()

        if existing:
            db_analysis = existing
        else:
            db_analysis = Analysis(listing_id=listing.id)
            self.db.add(db_analysis)

        # Stage 1
        db_analysis.population_data = analysis["population"]
        db_analysis.demand_profile = analysis["demand_profile"]

        # Stage 2
        db_analysis.insurability = analysis["insurability"]
        db_analysis.image_analysis = analysis["image_analysis"]
        db_analysis.vision_photos_hash = analysis.get("vision_photos_hash")
        db_analysis.subdivision_input_hash = analysis.get("subdivision_input_hash")
        db_analysis.renovation_estimate = analysis["renovation"]
        db_analysis.timeline_estimate = analysis["timeline"]
        db_analysis.arv_estimate = analysis["arv"]
        db_analysis.rental_estimate = analysis["rental_income"]
        db_analysis.council_rates = analysis["council_rates"]
        db_analysis.subdivision_analysis = analysis["subdivision"]

        # Stage 3
        db_analysis.flip_financials = financials["flip"]
        db_analysis.rental_financials = financials["rental"]
        db_analysis.strategy_decision = financials["strategy"]

        # Scoring
        db_analysis.composite_score = scoring["composite_score"]
        db_analysis.component_scores = scoring["component_scores"]
        db_analysis.verdict = scoring["verdict"]
        db_analysis.flags = scoring["flags"]
        db_analysis.next_steps = scoring["next_steps"]
        db_analysis.confidence_level = scoring["confidence_level"]

        self.db.commit()

    def _rerank_all(self):
        """Re-rank all analyzed listings by composite score."""
        analyses = (
            self.db.query(Analysis)
            .filter(Analysis.composite_score.isnot(None))
            .order_by(Analysis.composite_score.desc())
            .all()
        )

        for i, analysis in enumerate(analyses, 1):
            analysis.rank = i

        self.db.commit()
        logger.info(f"Re-ranked {len(analyses)} listings")

    def _listing_to_dict(self, listing: Listing) -> dict:
        """Convert Listing ORM object to dict for analysis functions."""
        effective_price = get_effective_asking_price(listing)
        return {
            "listing_id": listing.listing_id,
            "address": listing.address,
            "full_address": listing.full_address,
            "suburb": listing.suburb,
            "district": listing.district,
            "region": listing.region,
            "geographic_location": listing.geographic_location or "",
            "bedrooms": listing.bedrooms,
            "bathrooms": listing.bathrooms,
            "land_area": listing.land_area,
            "floor_area": listing.floor_area,
            "property_type": listing.property_type,
            "asking_price": effective_price,
            "capital_value": listing.capital_value,
            "title": listing.title,
            "description": listing.description,
        }
