#!/usr/bin/env python3
"""
Quick test of Vertex AI Gemini vision on a single image URL.
Run from backend/: python scripts/test_vision_vertex.py [image_url]
"""
import json
import logging
import sys
from pathlib import Path

# Add backend to path
backend = Path(__file__).resolve().parent.parent
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s [%(name)s] %(message)s", stream=sys.stdout)

# Default: Google's canonical test image (works with Vertex)
DEFAULT_IMAGE_URL = "https://storage.googleapis.com/cloud-samples-data/generative-ai/image/scones.jpg"

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE_URL
    print("=" * 72)
    print("  Vertex AI Gemini Vision Test")
    print("=" * 72)
    print(f"\n  Image URL: {url}")
    print(f"  VISION_PROVIDER must be 'vertex' in .env\n")

    from app.config import settings
    from app.services.external.vision_api import VisionAPIClient

    print(f"  VISION_PROVIDER from .env: {settings.vision_provider}")
    print(f"  GOOGLE_CLOUD_PROJECT: {settings.google_cloud_project}")
    print(f"  GOOGLE_CLOUD_LOCATION: {settings.google_cloud_location}")
    print()

    client = VisionAPIClient()
    if client.provider != "vertex":
        print(f"  ERROR: Provider is '{client.provider}', not 'vertex'. Check .env")
        return 1

    print("  Calling analyze_listing_photos([url])...")
    print("-" * 72)
    result = client.analyze_listing_photos([url])
    print("-" * 72)
    print("\n  RESULT (verbose):")
    print(json.dumps(result, indent=2, default=str))
    print("\n  Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
