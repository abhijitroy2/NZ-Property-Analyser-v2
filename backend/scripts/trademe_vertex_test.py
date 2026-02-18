#!/usr/bin/env python3
"""
Fetch TradeMe listing photos and run Vertex AI analysis with full capture.
Builds JSON extractor from raw Gemini responses.

Usage: python scripts/trademe_vertex_test.py [listing_url_or_id]
Default: https://www.trademe.co.nz/a/property/residential/sale/waikato/south-waikato/tokoroa/listing/5660763654
"""
import json
import re
import sys
import logging
from pathlib import Path
from urllib.parse import urlparse

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)

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

def extract_json_from_text(text: str) -> tuple[dict | None, str]:
    """
    Extract JSON object from model response. Handles:
    - Raw JSON
    - Markdown code blocks: ```json ... ``` or ``` ... ```
    - Text before/after JSON
    Returns (parsed_dict, raw_extracted) or (None, full_text on parse error)
    """
    if not text or not text.strip():
        return None, text or ""

    # Try markdown code block first (```json ... ``` or ``` ... ```)
    for pattern in [
        r"```(?:json)?\s*\n?([\s\S]*?)```",
        r"```(?:json)?\s*([\s\S]*?)```",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            block = m.group(1).strip()
            start = block.find("{")
            end = block.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(block[start:end]), block[start:end]
                except json.JSONDecodeError:
                    pass

    # Fallback: find outermost {...}
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end]), text[start:end]
        except json.JSONDecodeError as e:
            # Try to fix common issues: trailing comma, unescaped newlines
            raw = text[start:end]
            fixed = re.sub(r",\s*}", "}", raw)  # trailing comma before }
            fixed = re.sub(r",\s*]", "]", fixed)  # trailing comma before ]
            try:
                return json.loads(fixed), raw
            except json.JSONDecodeError:
                return None, text
    return None, text

def main():
    identifier = sys.argv[1] if len(sys.argv) > 1 else "5660763654"
    try:
        listing_id = extract_listing_id(identifier)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    print("=" * 72)
    print("  TradeMe Listing -> Vertex AI Vision Test")
    print("=" * 72)
    print(f"\n  Listing ID: {listing_id}")

    # Fetch photos
    print("\n  Fetching photos from TradeMe API...")
    try:
        photos = fetch_listing_photos(listing_id)
        print(f"  Found {len(photos)} photo(s)")
        for i, url in enumerate(photos[:6], 1):
            print(f"    [{i}] {url[:70]}...")
    except Exception as e:
        print(f"  ERROR fetching photos: {e}")
        return 1

    if not photos:
        print("  No photos available.")
        return 1

    # Import Vertex client
    from app.config import settings
    from app.services.external.vision_api import ANALYSIS_PROMPT, SUMMARY_PROMPT
    from google import genai
    from google.genai.types import Part, HttpOptions
    import requests

    if settings.vision_provider != "vertex":
        print(f"\n  WARNING: VISION_PROVIDER is '{settings.vision_provider}', not 'vertex'.")
        print("  Attempting anyway...")

    import os
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", settings.google_cloud_project or "")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", settings.google_cloud_location or "us-central1")
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

    client = genai.Client(http_options=HttpOptions(api_version="v1"))

    # Analyze each photo and capture raw responses
    individual_analyses = []
    photos_to_analyze = photos[:6]

    print("\n" + "-" * 72)
    print("  PHOTO-BY-PHOTO ANALYSIS (raw responses captured)")
    print("-" * 72)

    for i, photo_url in enumerate(photos_to_analyze, 1):
        print(f"\n  --- Photo {i}/{len(photos_to_analyze)} ---")
        print(f"  URL: {photo_url[:60]}...")
        try:
            resp = requests.get(photo_url, timeout=15)
            resp.raise_for_status()
            img_bytes = resp.content
            mime = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip() or "image/jpeg"
            image_part = Part.from_bytes(data=img_bytes, mime_type=mime)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    ANALYSIS_PROMPT + "\n\nReturn only valid JSON, no markdown.",
                    image_part,
                ],
                config={"max_output_tokens": 2048, "temperature": 0.2},
            )
            raw_text = response.text or ""

            print(f"\n  RAW RESPONSE (first 600 chars):")
            print(f"  {raw_text[:600]!r}")
            print(f"\n  FULL RAW LENGTH: {len(raw_text)} chars")

            parsed, extracted = extract_json_from_text(raw_text)
            if parsed:
                parsed["source"] = "vertex_ai"
                individual_analyses.append(parsed)
                print(f"\n  PARSED OK: photo_type={parsed.get('photo_type')}, condition_rating={parsed.get('condition_rating')}")
                print(f"  FULL PARSED JSON:")
                print("  " + json.dumps(parsed, indent=4).replace("\n", "\n  "))
            else:
                print(f"\n  PARSE FAILED - extracted snippet: {extracted[:200]!r}")
        except Exception as e:
            print(f"\n  ERROR: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 72)
    print("  SUMMARY (overall renovation assessment)")
    print("=" * 72)

    if not individual_analyses:
        print("\n  No valid analyses - cannot summarize.")
        return 1

    print(f"\n  Individual analyses ({len(individual_analyses)}):")
    for i, a in enumerate(individual_analyses, 1):
        print(f"    [{i}] {a.get('photo_type','?')} | rating {a.get('condition_rating')} | {a.get('estimated_age','')}")

    # Call summary
    summary_prompt = SUMMARY_PROMPT + json.dumps(individual_analyses, indent=2) + "\n\nReturn only valid JSON."
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[summary_prompt],
            config={"max_output_tokens": 4096, "temperature": 0.2},
        )
        raw_summary = response.text or ""
        print(f"\n  RAW SUMMARY RESPONSE (first 800 chars):")
        print(f"  {raw_summary[:800]!r}")

        parsed_summary, _ = extract_json_from_text(raw_summary)
        if parsed_summary:
            print("\n  PARSED SUMMARY:")
            print(json.dumps(parsed_summary, indent=2))
            print("\n  KEY RENOVATION LEVEL:", parsed_summary.get("overall_reno_level", "?"))
        else:
            print("\n  Summary parse failed - using heuristic fallback")
            from app.services.external.vision_api import VisionAPIClient
            v = VisionAPIClient()
            fallback = v._summarize_heuristic(individual_analyses)
            print(json.dumps(fallback, indent=2))
    except Exception as e:
        print(f"\n  Summary ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n  Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
