"""
TradeMe Property Scraper Service.
Adapted from TM-scraper-1 to work as an importable service with DB storage.
"""

import re
import time
import logging
from urllib.parse import urlparse
from typing import List, Dict, Optional, Any
from datetime import datetime

import requests
import pytz
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sqlalchemy.orm import Session

from app.models.listing import Listing

logger = logging.getLogger(__name__)

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Host": "api.trademe.co.nz",
    "Origin": "https://www.trademe.co.nz",
    "Referer": "https://www.trademe.co.nz/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
}

TIMEOUT = 30


def _create_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _convert_date(date_str: str) -> Optional[datetime]:
    """Convert TradeMe date format to datetime."""
    try:
        ts_str = date_str.split("(")[1].split(")")[0]
        dt = datetime.fromtimestamp(int(ts_str) / 1000)
        local = dt.astimezone(pytz.timezone("Pacific/Auckland"))
        return local
    except (IndexError, ValueError, TypeError):
        return None


def _parse_price(price_str: str) -> Optional[float]:
    """Parse a display price string into a numeric value."""
    if not price_str:
        return None

    text = price_str.upper().strip()

    # Handle "By Negotiation", "Tender", "Auction", "PBN" etc.
    non_price_keywords = ["NEGOT", "TENDER", "AUCTION", "PBN", "ENQUIR", "DEADLINE"]
    if any(kw in text for kw in non_price_keywords):
        return None

    # Try to find numbers
    # Handle ranges like "$270,000 - $305,000" -> take midpoint
    range_match = re.findall(r"\$?([\d,]+\.?\d*)\s*[Kk]?\s*[-–to]+\s*\$?([\d,]+\.?\d*)\s*[Kk]?", text)
    if range_match:
        low_str, high_str = range_match[0]
        low = float(low_str.replace(",", ""))
        high = float(high_str.replace(",", ""))
        # Handle K suffix
        if "K" in text:
            if low < 10000:
                low *= 1000
            if high < 10000:
                high *= 1000
        return (low + high) / 2

    # Single price: "$450,000" or "$450K" or "$1.2M"
    single_match = re.search(r"\$?([\d,]+\.?\d*)\s*([KkMmBb])?", text)
    if single_match:
        value = float(single_match.group(1).replace(",", ""))
        suffix = (single_match.group(2) or "").upper()
        if suffix == "K":
            value *= 1000
        elif suffix == "M":
            value *= 1_000_000
        elif suffix == "B":
            value *= 1_000_000_000
        if value > 1000:  # Sanity check - should be at least $1000
            return value

    return None


def _parse_area(area_str: str) -> Optional[float]:
    """Parse an area string like '650 m²' into a float."""
    if not area_str:
        return None
    match = re.search(r"([\d,.]+)", str(area_str))
    if match:
        return float(match.group(1).replace(",", ""))
    return None


def _parse_nearby_properties(nearby_text: str) -> List[Dict[str, Any]]:
    """Parse the nearby properties text into structured data."""
    if not nearby_text:
        return []

    properties = []
    for line in nearby_text.split("\r\n"):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(";;")]
        prop = {}
        if len(parts) >= 1:
            prop["address"] = parts[0]
        if len(parts) >= 2:
            prop["date"] = parts[1]
        if len(parts) >= 3:
            prop["price"] = parts[2]
            prop["price_numeric"] = _parse_price(parts[2])
        if len(parts) >= 4:
            prop["url"] = parts[3]
        if prop:
            properties.append(prop)

    return properties


class TradeMeScraper:
    """Service to scrape TradeMe property listings and store in database."""

    def __init__(self, db: Session):
        self.db = db
        self.session = _create_session()

    def scrape_search_url(self, url: str) -> List[Listing]:
        """
        Scrape all listings from a TradeMe search URL and store in database.
        Returns list of new/updated Listing objects.
        """
        logger.info(f"Scraping search URL: {url}")
        raw_listings = self._fetch_listings(url)
        logger.info(f"Found {len(raw_listings)} raw listings")

        stored = []
        for i, raw in enumerate(raw_listings, 1):
            listing_id = str(raw.get("ListingId", ""))
            if not listing_id:
                continue

            logger.info(f"  Processing listing {i}/{len(raw_listings)}: {listing_id}")

            # Fetch details
            details = self._fetch_listing_details(raw)

            # Store / update in DB
            db_listing = self._store_listing(details, url)
            if db_listing:
                stored.append(db_listing)

            # Be polite to the API
            time.sleep(0.5)

        self.db.commit()
        logger.info(f"Stored/updated {len(stored)} listings from {url}")
        return stored

    def _fetch_listings(self, url: str) -> List[Dict]:
        """Fetch all listing summaries from a search URL."""
        API_URL = "https://api.trademe.co.nz/v1/search/property/residential.json"

        parsed = urlparse(url)
        path = parsed.path
        canonical_path = ""
        if path.split("/")[-1] == "search" and len(path.split("/")) > 3:
            canonical_path = "/" + "/".join(path.split("/")[2:-1])

        # Parse query params
        api_params = {}
        if parsed.query:
            for param in parsed.query.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    if key in api_params:
                        api_params[key] += "," + value
                    else:
                        api_params[key] = value

        api_params.update({
            "page": "1",
            "rows": "22",
            "return_canonical": "true",
            "return_metadata": "true",
            "canonical_path": canonical_path,
            "return_variants": "true",
            "snap_parameters": "true",
        })

        listings = []
        try:
            resp = self.session.get(API_URL, params=api_params, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            total = data.get("TotalCount", 0)
            listings.extend(data.get("List", []))

            total_pages = (total // 22) + (1 if total % 22 > 0 else 0)
            for page in range(2, total_pages + 1):
                api_params["page"] = str(page)
                retries = 3
                while retries > 0:
                    try:
                        resp = self.session.get(API_URL, params=api_params, headers=HEADERS, timeout=TIMEOUT)
                        resp.raise_for_status()
                        data = resp.json()
                        listings.extend(data.get("List", []))
                        break
                    except requests.exceptions.RequestException as e:
                        retries -= 1
                        if retries > 0:
                            wait_time = (4 - retries) * 2
                            logger.warning(f"Retry in {wait_time}s... ({retries} left)")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Failed page {page}: {e}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching listings: {e}")

        return listings

    def _fetch_listing_details(self, raw_listing: Dict) -> Dict[str, Any]:
        """Fetch detailed info for a single listing."""
        listing_id = raw_listing.get("ListingId")
        result = {
            "listing_id": str(listing_id),
            "title": raw_listing.get("Title", ""),
            "address": raw_listing.get("Address", ""),
            "suburb": raw_listing.get("Suburb", ""),
            "district": raw_listing.get("District", ""),
            "region": raw_listing.get("Region", ""),
            "geographic_location": str(raw_listing.get("GeographicLocation", "")),
            "display_price": raw_listing.get("PriceDisplay", ""),
        }

        # Full address
        result["full_address"] = ", ".join(
            filter(None, [result["address"], result["suburb"], result["district"], result["region"]])
        )

        # Published date
        date_list = raw_listing.get("PropertySearchListingsTag", [])
        if date_list and isinstance(date_list, list):
            date_str = date_list[0].get("Date", "")
            if date_str:
                result["listing_date"] = _convert_date(date_str)

        # Parse asking price
        result["asking_price"] = _parse_price(result["display_price"])

        # Canonical path for URL
        prop_path = raw_listing.get("CanonicalPath", "")
        result["property_url"] = f"https://www.trademe.co.nz/a{prop_path}" if prop_path else ""

        # Fetch full listing details
        detail_url = f"https://api.trademe.co.nz/v1/listings/{listing_id}.json?return_canonical=true&return_member_profile=true&return_variants=true"
        listing_data = {}
        try:
            resp = self.session.get(detail_url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            listing_data = resp.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed details for {listing_id}: {e}")

        # Description
        result["description"] = listing_data.get("Body", "")

        # Photos
        photos = listing_data.get("Photos", [])
        result["photos"] = [
            p.get("Value", {}).get("FullSize", "") or p.get("Value", {}).get("Large", "")
            for p in photos
            if p.get("Value")
        ]

        # Attributes
        attrs = listing_data.get("Attributes", [])
        for attr in attrs:
            name = attr.get("Name", "")
            value = attr.get("Value", "")
            if name == "bedrooms":
                result["bedrooms"] = int(value.split()[0]) if value else None
            elif name == "bathrooms":
                result["bathrooms"] = int(value.split()[0]) if value else None
            elif name == "land_area":
                result["land_area"] = _parse_area(value)
            elif name == "floor_area":
                result["floor_area"] = _parse_area(value)
            elif name == "rateable_value_(rv)":
                result["capital_value"] = value
            elif name == "property_type":
                result["property_type"] = value
            elif name == "title_type":
                result["title_type"] = value

        # Estimates
        est_url = f"https://api.trademe.co.nz/v1/property/research/estimates/{listing_id}.json"
        try:
            resp = self.session.get(est_url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            est_data = resp.json()
            prop_est = est_data.get("PropertyEstimates", {})
            if prop_est:
                result["estimated_market_price"] = prop_est.get("EstimatedMarketPriceRangeDisplay", "")
            rent_est = est_data.get("RentEstimates", {})
            if rent_est:
                result["estimated_weekly_rent"] = rent_est.get("EstimatedPricePerWeekRangeDisplay", "")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed estimates for {listing_id}: {e}")

        # Nearby properties
        home_id = None
        prop_attrs = listing_data.get("PropertyAttributes", [])
        for pa in prop_attrs:
            if pa.get("Name") == "homes_property_id":
                home_id = pa.get("Value")
                break

        if home_id:
            beds = result.get("bedrooms", 3) or 3
            if beds < 2:
                beds = 2
            nearby_url = (
                f"https://api.trademe.co.nz/v1/property/homes/nearby.json"
                f"?property_id={home_id}&bedrooms_min={beds-1}&bedrooms_max={beds+1}&limit=10"
            )
            try:
                resp = self.session.get(nearby_url, headers=HEADERS, timeout=TIMEOUT)
                resp.raise_for_status()
                cards = resp.json().get("Cards", [])
                nearby = []
                for card in cards:
                    pd_data = card.get("PropertyDetails", {})
                    nearby.append({
                        "address": pd_data.get("DisplayAddress", ""),
                        "date": card.get("Date", "").split("T")[0],
                        "price": card.get("DisplayPrice", ""),
                        "price_numeric": _parse_price(card.get("DisplayPrice", "")),
                        "url": f"https://www.trademe.co.nz/a{card.get('Url', '')}",
                    })
                result["nearby_properties"] = nearby
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed nearby for {listing_id}: {e}")

        return result

    def _store_listing(self, details: Dict[str, Any], source_url: str) -> Optional[Listing]:
        """Store or update a listing in the database."""
        listing_id = details.get("listing_id")
        if not listing_id:
            return None

        try:
            # Check if exists
            existing = self.db.query(Listing).filter(Listing.listing_id == listing_id).first()

            if existing:
                # Update existing
                for key, value in details.items():
                    if key != "listing_id" and hasattr(existing, key) and value:
                        setattr(existing, key, value)
                existing.source_url = source_url
                self.db.flush()
                return existing
            else:
                # Create new
                db_listing = Listing(
                    listing_id=listing_id,
                    title=details.get("title", ""),
                    address=details.get("address", ""),
                    full_address=details.get("full_address", ""),
                    suburb=details.get("suburb", ""),
                    district=details.get("district", ""),
                    region=details.get("region", ""),
                    geographic_location=details.get("geographic_location", ""),
                    bedrooms=details.get("bedrooms"),
                    bathrooms=details.get("bathrooms"),
                    land_area=details.get("land_area"),
                    floor_area=details.get("floor_area"),
                    capital_value=details.get("capital_value", ""),
                    property_type=details.get("property_type", ""),
                    title_type=details.get("title_type", ""),
                    display_price=details.get("display_price", ""),
                    asking_price=details.get("asking_price"),
                    estimated_market_price=details.get("estimated_market_price", ""),
                    estimated_weekly_rent=details.get("estimated_weekly_rent", ""),
                    description=details.get("description", ""),
                    property_url=details.get("property_url", ""),
                    photos=details.get("photos", []),
                    nearby_properties=details.get("nearby_properties", []),
                    listing_date=details.get("listing_date"),
                    source_url=source_url,
                    filter_status="pending",
                    analysis_status="pending",
                )
                self.db.add(db_listing)
                self.db.flush()
                return db_listing
        except Exception as e:
            logger.warning(f"Failed to store listing {listing_id}: {e}")
            self.db.rollback()
            # Try to return existing after rollback
            existing = self.db.query(Listing).filter(Listing.listing_id == listing_id).first()
            return existing
