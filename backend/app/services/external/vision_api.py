"""
AI Vision API Service.
Analyzes property listing photos to assess renovation needs.
Supports OpenAI GPT-4V, Anthropic Claude Vision, Google Cloud Vision,
Vertex AI Gemini, or mock mode.
"""

import json
import logging
import os
import re
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
  "overall_reno_level": "NONE" | "COSMETIC" | "MODERATE" | "MAJOR" | "FULL_GUT",
  "key_renovation_items": ["list of main renovation tasks needed"],
  "confidence": "HIGH" | "MEDIUM" | "LOW"
}

Individual photo analyses:
"""

# Single-call multi-image prompt (OpenAI only) — combines per-photo and summary in one request
MULTI_IMAGE_PROMPT = """You are analyzing property listing photos for renovation assessment (NZ context). These {n} photos show different views of the property. Return a single JSON object with these required fields:

{{
  "roof_condition": "NEW_IRON" | "OLD_IRON" | "TILES" | "NEEDS_REPLACE" | "UNKNOWN",
  "exterior_condition": "EXCELLENT" | "GOOD" | "FAIR" | "POOR",
  "interior_quality": "MODERN" | "DATED" | "VERY_DATED" | "DERELICT",
  "kitchen_age": "0-5yr" | "5-10yr" | "10-20yr" | "20+yr" | "UNKNOWN",
  "bathroom_age": "0-5yr" | "5-10yr" | "10-20yr" | "20+yr" | "UNKNOWN",
  "structural_concerns": ["list of visible structural issues if any"],
  "overall_reno_level": "NONE" | "COSMETIC" | "MODERATE" | "MAJOR" | "FULL_GUT",
  "key_renovation_items": ["list of main renovation tasks needed"],
  "confidence": "HIGH" | "MEDIUM" | "LOW"
}}

Optionally include: flip_plan (list), rental_minimum_plan (list), healthy_homes_risks_visible (list), due_diligence_checks (list).

Be specific and practical. Focus on renovation-relevant details. Return only valid JSON, no markdown."""


def _extract_json_from_response(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON object from Gemini response. Handles markdown code blocks,
    truncated output, and text wrapping.
    """
    if not text or not text.strip():
        return None
    # Strip ```json or ``` prefix if present (handles truncated responses without closing ```)
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"```\s*$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start >= 0 and end > start:
        raw = cleaned[start:end]
        for candidate in [raw, re.sub(r",\s*}", "}", raw), re.sub(r",\s*]", "]", raw)]:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    return None


class VisionAPIClient:
    """AI Vision client for property photo analysis."""

    def __init__(self):
        self.provider = settings.vision_provider
        self._google_client = None
        self._vertex_client = None

        # Set up Vertex AI env for Gemini (VISION_PROVIDER=vertex)
        if self.provider == "vertex":
            if settings.google_cloud_project:
                os.environ.setdefault("GOOGLE_CLOUD_PROJECT", settings.google_cloud_project)
            os.environ.setdefault("GOOGLE_CLOUD_LOCATION", settings.google_cloud_location)
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
            try:
                from google import genai
                from google.genai.types import HttpOptions
                self._vertex_client = genai.Client(http_options=HttpOptions(api_version="v1"))
                logger.info("Vertex AI Gemini client initialised successfully")
            except Exception as e:
                logger.error(f"Failed to initialise Vertex AI client: {e}")
                logger.warning("Falling back to mock provider")
                self.provider = "mock"

        # Set up Google Vision credentials if configured
        elif self.provider == "google":
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

        # OpenAI: single multi-image call (cost-effective, 1 API call)
        if self.provider == "openai":
            return self._analyze_openai_multi(photos)

        # Vertex, Anthropic, Google: per-photo analysis + summary
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
        elif self.provider == "vertex":
            return self._analyze_vertex(photo_url)
        return None

    def _analyze_openai(self, photo_url: str) -> Optional[Dict[str, Any]]:
        """Analyze photo using OpenAI vision model (cost-effective default)."""
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured")
            return None
        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)

            prompt = ANALYSIS_PROMPT + "\n\nReturn only valid JSON, no markdown."
            response = client.chat.completions.create(
                model=getattr(settings, "openai_vision_model", "gpt-4o-mini") or "gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": photo_url}},
                        ],
                    }
                ],
                max_tokens=2048,
                response_format={"type": "json_object"},
            )

            text = response.choices[0].message.content or ""
            result = _extract_json_from_response(text) or (json.loads(text) if text else None)
            if result:
                result["source"] = "openai"
                return result
            return None
        except Exception as e:
            logger.warning(f"OpenAI vision analysis failed: {e}")
            return None

    def _analyze_openai_multi(self, photos: List[str]) -> Dict[str, Any]:
        """
        Single multi-image API call for OpenAI. Combines analysis + summary in one request.
        Uses first 6 photos. On failure or invalid JSON, falls back to heuristic (no per-photo data).
        """
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured")
            return self._summarize_heuristic([])
        photos_to_send = photos[:6]
        if not photos_to_send:
            return self._default_analysis()
        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)

            content: List[Dict[str, Any]] = [
                {"type": "text", "text": MULTI_IMAGE_PROMPT.format(n=len(photos_to_send)) + "\n\nReturn only valid JSON, no markdown."}
            ]
            for url in photos_to_send:
                content.append({"type": "image_url", "image_url": {"url": url}})

            response = client.chat.completions.create(
                model=getattr(settings, "openai_vision_model", "gpt-4o-mini") or "gpt-4o-mini",
                messages=[{"role": "user", "content": content}],
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            text = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            if usage:
                logger.info(
                    "OpenAI multi-image: prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                    getattr(usage, "prompt_tokens", "-"),
                    getattr(usage, "completion_tokens", "-"),
                    getattr(usage, "total_tokens", "-"),
                )
            result = _extract_json_from_response(text) or (json.loads(text) if text else None)
            if result and isinstance(result, dict):
                return result
        except Exception as e:
            logger.warning(f"OpenAI multi-image analysis failed: {e}")
        return self._summarize_heuristic([])

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

    def _analyze_vertex(self, photo_url: str) -> Optional[Dict[str, Any]]:
        """Analyze photo using Vertex AI Gemini (image understanding)."""
        if not self._vertex_client:
            return None
        try:
            from google.genai.types import Part

            # Download image for reliable handling (HTTP URLs can be flaky with Vertex)
            resp = requests.get(photo_url, timeout=15)
            resp.raise_for_status()
            img_bytes = resp.content
            mime = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip() or "image/jpeg"
            image_part = Part.from_bytes(data=img_bytes, mime_type=mime)

            response = self._vertex_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    ANALYSIS_PROMPT + "\n\nReturn only valid JSON, no markdown.",
                    image_part,
                ],
                config={"max_output_tokens": 2048, "temperature": 0.2},
            )
            text = response.text or ""
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(text[start:end])
                result["source"] = "vertex_ai"
                return result
            logger.warning("Vertex AI did not return valid JSON")
            return None
        except Exception as e:
            logger.warning(f"Vertex AI vision analysis failed: {e}")
            return None

    def _summarize_vertex(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use Vertex AI Gemini to summarize individual analyses."""
        if not self._vertex_client:
            return self._summarize_heuristic(analyses)
        try:
            response = self._vertex_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    SUMMARY_PROMPT + json.dumps(analyses, indent=2) + "\n\nReturn only valid JSON.",
                ],
                config={"max_output_tokens": 4096, "temperature": 0.2},
            )
            text = response.text or ""
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception as e:
            logger.warning(f"Vertex AI summary failed: {e}")
        return self._summarize_heuristic(analyses)

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
        elif self.provider == "vertex":
            return self._summarize_vertex(analyses)
        # Google Vision uses heuristic summary (no LLM for summarisation)
        return self._summarize_heuristic(analyses)

    def _summarize_openai(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use OpenAI to summarize individual analyses."""
        if not settings.openai_api_key:
            return self._summarize_heuristic(analyses)
        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)

            # OpenAI-only extension: add flip vs rental/Healthy Homes guidance while preserving
            # the existing required schema keys used by downstream code.
            extra = (
                "\n\nAdditionally include these OPTIONAL keys in the JSON output (do not remove/rename any existing keys):\n"
                "- flip_plan: list of high-ROI renovation items + sequencing notes\n"
                "- rental_minimum_plan: list of minimum works to reduce Healthy Homes risk (heating/ventilation/insulation cues)\n"
                "- healthy_homes_risks_visible: list of photo-based risk cues (e.g., mould/condensation) if any\n"
                "- due_diligence_checks: list of checks not verifiable from photos (e.g., insulation statement, extractor fans ducted)\n"
            )
            content = SUMMARY_PROMPT + json.dumps(analyses, indent=2) + extra + "\nReturn only valid JSON."
            response = client.chat.completions.create(
                model=getattr(settings, "openai_summary_model", "gpt-4o-mini") or "gpt-4o-mini",
                messages=[{"role": "user", "content": content}],
                max_tokens=2048,
                response_format={"type": "json_object"},
            )

            text = response.choices[0].message.content or ""
            result = _extract_json_from_response(text) or (json.loads(text) if text else None)
            if result:
                return result
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
        def _rating(a: Dict) -> int:
            v = a.get("condition_rating")
            return int(v) if v is not None else 5
        avg_rating = sum(_rating(a) for a in analyses) / len(analyses) if analyses else 5

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
