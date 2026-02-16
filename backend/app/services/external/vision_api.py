"""
AI Vision API Service.
Analyzes property listing photos to assess renovation needs.
Supports OpenAI GPT-4V, Anthropic Claude Vision, Google Cloud Vision, or mock mode.
"""

import json
import logging
import os
import base64
from typing import Dict, Any, List, Optional

import requests

from app.config import settings

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Analyze this property listing photo and assess its condition. Return a JSON object with the following fields:

{
  "photo_type": "exterior" | "interior" | "kitchen" | "bathroom" | "roof" | "garden" | "other",
  "condition_rating": 1-10 (1=derelict, 10=brand new),
  "observations": ["list of key observations"],
  "issues_detected": ["list of any problems or concerns"],
  "estimated_age": "approximate age description (e.g., '1960s bungalow', 'modern 2010s')",
  "renovation_indicators": {
    "needs_paint": true/false,
    "dated_fixtures": true/false,
    "structural_concerns": true/false,
    "moisture_damage": true/false,
    "roof_issues": true/false,
    "needs_kitchen_update": true/false,
    "needs_bathroom_update": true/false
  }
}

Be specific and practical in your assessment. Focus on renovation-relevant details."""

SUMMARY_PROMPT = """Based on these individual photo analyses of a property listing, provide an overall renovation assessment. Return a JSON object:

{
  "roof_condition": "NEW_IRON" | "OLD_IRON" | "TILES" | "NEEDS_REPLACE" | "UNKNOWN",
  "exterior_condition": "EXCELLENT" | "GOOD" | "FAIR" | "POOR",
  "interior_quality": "MODERN" | "DATED" | "VERY_DATED" | "DERELICT",
  "kitchen_age": "0-5yr" | "5-10yr" | "10-20yr" | "20+yr" | "UNKNOWN",
  "bathroom_age": "0-5yr" | "5-10yr" | "10-20yr" | "20+yr" | "UNKNOWN",
  "structural_concerns": ["list of visible structural issues"],
  "overall_reno_level": "COSMETIC" | "MODERATE" | "MAJOR" | "FULL_GUT",
  "key_renovation_items": ["list of main renovation tasks needed"],
  "confidence": "HIGH" | "MEDIUM" | "LOW"
}

Individual photo analyses:
"""


class VisionAPIClient:
    """AI Vision client for property photo analysis."""

    def __init__(self):
        self.provider = settings.vision_provider
        self._google_client = None

        # Set up Google Vision credentials if configured
        if self.provider == "google":
            cred_path = settings.google_vision_credentials
            if cred_path:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
                logger.info(f"Google Vision credentials set from: {cred_path}")
            try:
                from google.cloud import vision
                self._google_client = vision.ImageAnnotatorClient()
                logger.info("Google Cloud Vision client initialised successfully")
            except Exception as e:
                logger.error(f"Failed to initialise Google Vision client: {e}")
                logger.warning("Falling back to mock provider")
                self.provider = "mock"

    def analyze_listing_photos(self, photos: List[str]) -> Dict[str, Any]:
        """
        Analyze property listing photos and return renovation assessment.
        
        Args:
            photos: List of photo URLs.
        
        Returns:
            Dict with overall renovation assessment.
        """
        if not photos:
            return self._default_analysis()

        if self.provider == "mock":
            return self._mock_analysis(photos)

        # Analyze individual photos (limit to 6 to manage costs)
        photos_to_analyze = photos[:6]
        individual_analyses = []

        for photo_url in photos_to_analyze:
            try:
                analysis = self._analyze_single_photo(photo_url)
                if analysis:
                    individual_analyses.append(analysis)
            except Exception as e:
                logger.warning(f"Failed to analyze photo {photo_url}: {e}")

        if not individual_analyses:
            return self._default_analysis()

        # Get overall summary from individual analyses
        summary = self._get_summary(individual_analyses)
        return summary

    def _analyze_single_photo(self, photo_url: str) -> Optional[Dict[str, Any]]:
        """Analyze a single photo using the configured AI vision provider."""
        if self.provider == "openai":
            return self._analyze_openai(photo_url)
        elif self.provider == "anthropic":
            return self._analyze_anthropic(photo_url)
        elif self.provider == "google":
            return self._analyze_google(photo_url)
        return None

    def _analyze_openai(self, photo_url: str) -> Optional[Dict[str, Any]]:
        """Analyze photo using OpenAI GPT-4 Vision."""
        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": ANALYSIS_PROMPT},
                            {"type": "image_url", "image_url": {"url": photo_url}},
                        ],
                    }
                ],
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            text = response.choices[0].message.content
            return json.loads(text)
        except Exception as e:
            logger.warning(f"OpenAI vision analysis failed: {e}")
            return None

    def _analyze_anthropic(self, photo_url: str) -> Optional[Dict[str, Any]]:
        """Analyze photo using Anthropic Claude Vision."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

            # Download image and convert to base64
            resp = requests.get(photo_url, timeout=15)
            resp.raise_for_status()
            img_data = base64.standard_b64encode(resp.content).decode("utf-8")
            media_type = resp.headers.get("content-type", "image/jpeg")

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": img_data,
                                },
                            },
                            {"type": "text", "text": ANALYSIS_PROMPT + "\n\nReturn only valid JSON."},
                        ],
                    }
                ],
            )

            text = response.content[0].text
            # Try to extract JSON from response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception as e:
            logger.warning(f"Anthropic vision analysis failed: {e}")
        return None

    def _analyze_google(self, photo_url: str) -> Optional[Dict[str, Any]]:
        """Analyze photo using Google Cloud Vision API."""
        try:
            from google.cloud import vision

            # Build image source from URL
            image = vision.Image()
            image.source = vision.ImageSource(image_uri=photo_url)

            # Run multiple detection types in parallel
            features = [
                vision.Feature(type_=vision.Feature.Type.LABEL_DETECTION, max_results=20),
                vision.Feature(type_=vision.Feature.Type.OBJECT_LOCALIZATION, max_results=15),
                vision.Feature(type_=vision.Feature.Type.IMAGE_PROPERTIES),
            ]
            request = vision.AnnotateImageRequest(image=image, features=features)
            response = self._google_client.annotate_image(request=request)

            if response.error.message:
                logger.warning(f"Google Vision API error: {response.error.message}")
                return None

            # Extract labels and objects
            labels = [label.description.lower() for label in response.label_annotations]
            label_scores = {
                label.description.lower(): label.score
                for label in response.label_annotations
            }
            objects = [obj.name.lower() for obj in response.localized_object_annotations]

            all_detected = set(labels + objects)
            logger.debug(f"Google Vision detected: labels={labels}, objects={objects}")

            # --- Map detections to our renovation schema ---
            photo_type = self._google_classify_photo_type(all_detected)
            condition_rating = self._google_estimate_condition(labels, label_scores)
            observations = self._google_build_observations(labels, objects)
            issues = self._google_detect_issues(all_detected)
            reno_indicators = self._google_renovation_indicators(all_detected)

            return {
                "photo_type": photo_type,
                "condition_rating": condition_rating,
                "observations": observations[:8],
                "issues_detected": issues,
                "estimated_age": self._google_estimate_age(all_detected),
                "renovation_indicators": reno_indicators,
                "source": "google_vision",
            }
        except Exception as e:
            logger.warning(f"Google Vision analysis failed: {e}")
            return None

    # ---------- Google Vision helper methods ----------

    def _google_classify_photo_type(self, detected: set) -> str:
        """Classify photo type from Google Vision labels."""
        type_map = {
            "kitchen": "kitchen",
            "bathroom": "bathroom",
            "bathtub": "bathroom",
            "shower": "bathroom",
            "toilet": "bathroom",
            "sink": "bathroom",
            "roof": "roof",
            "roofing": "roof",
            "garden": "garden",
            "yard": "garden",
            "lawn": "garden",
            "backyard": "garden",
            "house": "exterior",
            "facade": "exterior",
            "building": "exterior",
            "porch": "exterior",
            "driveway": "exterior",
            "living room": "interior",
            "bedroom": "interior",
            "room": "interior",
            "floor": "interior",
            "ceiling": "interior",
            "window": "interior",
            "furniture": "interior",
        }
        for keyword, ptype in type_map.items():
            if keyword in detected:
                return ptype
        return "other"

    def _google_estimate_condition(self, labels: List[str], scores: Dict[str, float]) -> int:
        """Estimate condition rating (1-10) from label signals."""
        rating = 6  # neutral starting point

        positive_signals = [
            "modern", "new", "luxury", "contemporary", "renovation",
            "renovated", "clean", "polished", "elegant", "stylish",
        ]
        negative_signals = [
            "old", "aged", "worn", "damaged", "stain", "crack",
            "mold", "rust", "decay", "derelict", "abandoned",
            "dilapidated", "peeling", "broken",
        ]

        for label in labels:
            for pos in positive_signals:
                if pos in label:
                    rating += 1
                    break
            for neg in negative_signals:
                if neg in label:
                    rating -= 1
                    break

        return max(1, min(10, rating))

    def _google_build_observations(self, labels: List[str], objects: List[str]) -> List[str]:
        """Build human-readable observation list."""
        observations = []
        property_terms = {
            "house", "building", "room", "kitchen", "bathroom", "bedroom",
            "living room", "garden", "yard", "floor", "ceiling", "wall",
            "door", "window", "fence", "roof", "driveway", "furniture",
            "countertop", "cabinetry", "sink", "bathtub", "toilet",
            "staircase", "fireplace", "deck", "patio", "pool",
        }
        for label in labels:
            if label in property_terms or any(t in label for t in property_terms):
                observations.append(f"Detected: {label}")
        for obj in objects:
            if obj in property_terms or any(t in obj for t in property_terms):
                observations.append(f"Object: {obj}")
        return list(dict.fromkeys(observations))  # deduplicate preserving order

    def _google_detect_issues(self, detected: set) -> List[str]:
        """Detect potential issues from labels/objects."""
        issue_keywords = {
            "rust": "Rust or corrosion detected",
            "crack": "Cracks visible",
            "mold": "Possible mould/mildew",
            "stain": "Staining or water marks",
            "damage": "Visible damage",
            "peeling": "Peeling paint or surfaces",
            "decay": "Material decay detected",
            "weed": "Overgrown vegetation/weeds",
            "broken": "Broken elements detected",
            "leak": "Possible water leak signs",
        }
        issues = []
        for keyword, description in issue_keywords.items():
            if any(keyword in item for item in detected):
                issues.append(description)
        return issues

    def _google_renovation_indicators(self, detected: set) -> Dict[str, bool]:
        """Determine renovation indicators from detected features."""
        indicators = {
            "needs_paint": any(k in str(detected) for k in ["peeling", "faded", "stain", "worn"]),
            "dated_fixtures": any(k in str(detected) for k in ["vintage", "retro", "old", "antique", "dated"]),
            "structural_concerns": any(k in str(detected) for k in ["crack", "foundation", "lean", "sag"]),
            "moisture_damage": any(k in str(detected) for k in ["mold", "mould", "damp", "stain", "leak", "rust"]),
            "roof_issues": any(k in str(detected) for k in ["rust", "moss", "damaged roof", "missing"]),
            "needs_kitchen_update": any(k in str(detected) for k in ["dated", "old", "laminate"]) and "kitchen" in detected,
            "needs_bathroom_update": any(k in str(detected) for k in ["dated", "old", "stain"]) and ("bathroom" in detected or "bathtub" in detected),
        }
        return indicators

    def _google_estimate_age(self, detected: set) -> str:
        """Rough age estimation from visual cues."""
        if any(k in str(detected) for k in ["modern", "contemporary", "new"]):
            return "Modern (post-2010)"
        elif any(k in str(detected) for k in ["vintage", "retro", "antique"]):
            return "Pre-1970s"
        elif any(k in str(detected) for k in ["dated", "old"]):
            return "1970s-1990s era"
        return "Unable to determine from labels"

    def _get_summary(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get overall summary from individual photo analyses."""
        if self.provider == "openai":
            return self._summarize_openai(analyses)
        elif self.provider == "anthropic":
            return self._summarize_anthropic(analyses)
        # Google Vision uses heuristic summary (no LLM for summarisation)
        return self._summarize_heuristic(analyses)

    def _summarize_openai(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use OpenAI to summarize individual analyses."""
        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": SUMMARY_PROMPT + json.dumps(analyses, indent=2),
                    }
                ],
                max_tokens=600,
                response_format={"type": "json_object"},
            )

            text = response.choices[0].message.content
            return json.loads(text)
        except Exception as e:
            logger.warning(f"OpenAI summary failed: {e}")
            return self._summarize_heuristic(analyses)

    def _summarize_anthropic(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use Anthropic to summarize individual analyses."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=600,
                messages=[
                    {
                        "role": "user",
                        "content": SUMMARY_PROMPT + json.dumps(analyses, indent=2) + "\n\nReturn only valid JSON.",
                    }
                ],
            )

            text = response.content[0].text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception as e:
            logger.warning(f"Anthropic summary failed: {e}")
        return self._summarize_heuristic(analyses)

    def _summarize_heuristic(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Heuristic-based summary from individual analyses when AI unavailable."""
        avg_rating = sum(a.get("condition_rating", 5) for a in analyses) / len(analyses) if analyses else 5

        all_issues = []
        reno_indicators = {}
        for a in analyses:
            all_issues.extend(a.get("issues_detected", []))
            for k, v in a.get("renovation_indicators", {}).items():
                if v:
                    reno_indicators[k] = True

        # Map average rating to renovation level
        if avg_rating >= 8:
            reno_level = "COSMETIC"
        elif avg_rating >= 6:
            reno_level = "MODERATE"
        elif avg_rating >= 4:
            reno_level = "MAJOR"
        else:
            reno_level = "FULL_GUT"

        return {
            "roof_condition": "UNKNOWN",
            "exterior_condition": "GOOD" if avg_rating >= 6 else "FAIR" if avg_rating >= 4 else "POOR",
            "interior_quality": "MODERN" if avg_rating >= 8 else "DATED" if avg_rating >= 5 else "VERY_DATED",
            "kitchen_age": "UNKNOWN",
            "bathroom_age": "UNKNOWN",
            "structural_concerns": list(set(all_issues))[:5],
            "overall_reno_level": reno_level,
            "key_renovation_items": list(reno_indicators.keys()),
            "confidence": "LOW",
        }

    def _mock_analysis(self, photos: List[str]) -> Dict[str, Any]:
        """Conservative mock analysis when no vision API is configured."""
        return {
            "roof_condition": "UNKNOWN",
            "exterior_condition": "FAIR",
            "interior_quality": "DATED",
            "kitchen_age": "10-20yr",
            "bathroom_age": "10-20yr",
            "structural_concerns": [],
            "overall_reno_level": "MODERATE",
            "key_renovation_items": [
                "Paint interior/exterior",
                "Kitchen refresh",
                "Bathroom update",
                "Floor coverings",
            ],
            "confidence": "LOW",
            "source": "mock_default",
            "note": "Set VISION_PROVIDER in .env for AI-powered analysis",
        }

    def _default_analysis(self) -> Dict[str, Any]:
        """Default when no photos available."""
        return {
            "roof_condition": "UNKNOWN",
            "exterior_condition": "UNKNOWN",
            "interior_quality": "UNKNOWN",
            "kitchen_age": "UNKNOWN",
            "bathroom_age": "UNKNOWN",
            "structural_concerns": [],
            "overall_reno_level": "MODERATE",
            "key_renovation_items": [],
            "confidence": "LOW",
            "source": "no_photos",
        }
