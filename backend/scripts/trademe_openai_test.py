#!/usr/bin/env python3
"""
Fetch TradeMe listing photos and run OpenAI vision analysis via VisionAPIClient.

Usage:
  python scripts/trademe_openai_test.py [listing_id_or_url]
  python scripts/trademe_openai_test.py 5660763654 --verbose  # Verbose logging + save to logs/

Default listing: 5660763654
Pre-requisites: VISION_PROVIDER=openai and OPENAI_API_KEY in .env
"""
import json
import re
import sys
import logging
from datetime import datetime
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))

LOG_DIR = backend / "logs"
LOG_DIR.mkdir(exist_ok=True)

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
    "Referer": "https://www.trademe.co.nz/",
    "Origin": "https://www.trademe.co.nz",
}


def fetch_listing_photos(listing_id: str) -> list[str]:
    """Fetch photo URLs from TradeMe API."""
    import requests

    url = f"https://api.trademe.co.nz/v1/listings/{listing_id}.json?return_canonical=true&return_variants=true"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    photos = data.get("Photos", [])
    urls = []
    for p in photos:
        v = p.get("Value", {})
        url_str = v.get("FullSize") or v.get("Large") or v.get("Gallery") or ""
        if url_str:
            urls.append(url_str)
    return urls


def extract_listing_id(identifier: str) -> str:
    """Extract listing ID from URL or use as-is if numeric."""
    if identifier.isdigit():
        return identifier
    m = re.search(r"/listing/(\d+)", identifier)
    if m:
        return m.group(1)
    m = re.search(r"(\d{7,})", identifier)
    if m:
        return m.group(1)
    raise ValueError(f"Cannot extract listing ID from: {identifier}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("listing", nargs="?", default="5660763654", help="Listing ID or TradeMe URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging and save to logs/")
    args = parser.parse_args()

    identifier = args.listing
    verbose = args.verbose

    # Log file (when verbose)
    log_file = None
    if verbose:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            listing_id_preview = extract_listing_id(identifier)
        except ValueError:
            listing_id_preview = "unknown"
        log_path = LOG_DIR / f"trademe_openai_{listing_id_preview}_{timestamp}.log"
        log_file = open(log_path, "w", encoding="utf-8")

    def out(msg: str) -> None:
        print(msg)
        if log_file:
            log_file.write(msg + "\n")
            log_file.flush()

    # Logging config
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s [%(name)s] %(message)s", force=True)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        logging.getLogger("httpcore").setLevel(logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.DEBUG)
        logging.getLogger("openai").setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)

    # Capture logging to file when verbose
    if verbose and log_file:
        root = logging.getLogger()
        handler = logging.StreamHandler(log_file)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        root.addHandler(handler)

    try:
        listing_id = extract_listing_id(identifier)
    except ValueError as e:
        out(f"Error: {e}")
        if log_file:
            log_file.close()
        return 1

    if verbose and log_file:
        out(f"Log file: {log_path}")

    try:
        out("=" * 72)
        out("  TradeMe Listing -> OpenAI Vision Test")
        out("=" * 72)
        out(f"\n  Listing ID: {listing_id}")

        # Fetch photos
        out("\n  Fetching photos from TradeMe API...")
        try:
            photos = fetch_listing_photos(listing_id)
        except Exception as e:
            out(f"  ERROR fetching photos: {e}")
            return 1

        out(f"  Found {len(photos)} photo(s)")
        for i, url in enumerate(photos[:6], 1):
            out(f"    [{i}] {url[:70]}...")

        if not photos:
            out("  No photos available.")
            return 1

        from app.config import settings
        from app.services.external.vision_api import VisionAPIClient

        if settings.vision_provider != "openai":
            out(f"\n  WARNING: VISION_PROVIDER is '{settings.vision_provider}', not 'openai'.")
            out("  Attempting anyway...")

        if not settings.openai_api_key:
            out("\n  ERROR: OPENAI_API_KEY not set in .env")
            return 1

        client = VisionAPIClient()
        out(f"\n  VISION_PROVIDER: {client.provider}")

        out("\n  Calling analyze_listing_photos(photos[:6])...")
        out("-" * 72)
        result = client.analyze_listing_photos(photos[:6])
        out("-" * 72)

        out("\n  RESULT (full):")
        out(json.dumps(result, indent=2, default=str))

        out("\n  KEY FIELDS:")
        out(f"    overall_reno_level: {result.get('overall_reno_level', '?')}")
        out(f"    key_renovation_items: {result.get('key_renovation_items', [])}")
        if "healthy_homes_text" in result:
            out(f"    healthy_homes_text: {result.get('healthy_homes_text')}")

        if verbose and log_file:
            out(f"\n  Log saved to: {log_path}")
        out("\n  Done.")
        return 0
    finally:
        if log_file:
            log_file.close()


if __name__ == "__main__":
    sys.exit(main())
