"""
Gemini-based Fast Item Classification
======================================
Uses Google Gemini for quick, cost-effective item classification.
This is the PRIMARY analyzer for the "Analyze with AI" button.

Gemini handles:
- Basic item identification
- Brand/franchise detection
- Category classification
- Simple description generation
- Collectible YES/NO detection (triggers deep analysis)
- Basic value estimation

Claude handles deep collectible analysis (authentication, grading, variants).
"""

import os
import base64
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests

from ..schema.unified_listing import Photo


class GeminiClassifier:
    """
    Fast item classifier using Google Gemini.

    This is designed for speed and cost-efficiency.
    Use for initial classification before deep collectible analysis.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini classifier"""
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY or GEMINI_API_KEY must be set")

        # Use Gemini 1.5 Flash for speed and cost-efficiency
        # Image-capable models (v1 API endpoint):
        # - gemini-1.5-flash (recommended for speed/cost)
        # - gemini-1.5-flash-latest
        # - gemini-1.5-pro
        # - gemini-1.5-pro-latest
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        # CRITICAL: Use v1 endpoint (NOT v1beta) for Gemini 1.5 models
        self.api_url = f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent"

    def _encode_image_to_base64(self, image_path: str) -> str:
        """Encode local image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _get_image_mime_type(self, image_path: str) -> str:
        """Get MIME type from file extension"""
        ext = Path(image_path).suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_types.get(ext, "image/jpeg")

    def analyze_item(self, photos: List[Photo]) -> Dict[str, Any]:
        """
        Fast item classification using Gemini.

        Returns:
            {
                "item_name": str,
                "brand": str,
                "franchise": str,  # e.g., "Star Wars", "MLB", "Pokemon"
                "category": str,  # electronics, toys, apparel, home_goods, etc.
                "description": str,  # simple description
                "collectible": bool,  # YES/NO - triggers deep analysis
                "collectible_confidence": float,  # 0.0 to 1.0
                "collectible_indicators": List[str],  # what triggered collectible flag
                "estimated_value_low": float,
                "estimated_value_high": float,
                "detected_keywords": List[str],
                "sku_upc": str,  # if visible
                "logos_marks": List[str],
                "condition": str,  # new, like_new, good, fair, poor
                "color": str,
                "size": str,
                "material": str,
                "suggested_title": str,
                "suggested_price": float,
            }
        """
        if not photos:
            return {"error": "No photos provided"}

        # Prepare images for Gemini (limit to 4 photos for speed)
        image_parts = []
        for photo in photos[:4]:
            if photo.local_path:
                image_b64 = self._encode_image_to_base64(photo.local_path)
                mime_type = self._get_image_mime_type(photo.local_path)
                image_parts.append({
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_b64
                    }
                })

        # Build comprehensive classification prompt
        prompt = """Analyze these product images and provide a FAST, ACCURATE classification.

🔵 PRIMARY TASK: Item Classification

Identify:
1. Item name/type (what is this?)
2. Brand (Nike, Apple, Hasbro, etc.)
3. Franchise (Star Wars, MLB, Pokemon, Marvel, etc.)
4. Category (electronics, toys, apparel, home_goods, sports, collectibles, etc.)
5. Simple description (1-2 sentences)
6. Condition (new, like_new, good, fair, poor)
7. Color, size, material (if visible)
8. Any SKU, UPC, barcodes visible
9. Any logos, trademarks, marks
10. Detected keywords

🟢 COLLECTIBLE DETECTION (CRITICAL)

Mark collectible = TRUE if you see ANY of these:

**Brands & Franchises:**
- Pokemon (cards, toys, games, anything)
- MLB / NFL / NBA / NHL (any sports league items)
- Star Wars / Marvel / DC (any franchise items)
- Hot Wheels, Matchbox cars
- Barbie dolls
- Funko Pop figures
- Hallmark ornaments
- Disney items
- Vintage Coke, Pepsi, M&M tins
- Lego sets
- Anime merchandise
- Video game consoles or vintage games
- Magic: The Gathering, Yu-Gi-Oh cards
- Any autographed items

**Item Types:**
- Trading cards (sports, Pokemon, Magic, etc.)
- Action figures
- Vintage toys (1990s or earlier)
- Comics or graphic novels
- Coins, stamps, currency
- Sports memorabilia
- Vintage electronics
- Vintage tools
- Vintage clothing (band tees, jerseys, etc.)
- Limited edition items
- Numbered prints
- Vintage kitchenware (Pyrex, Fire King, etc.)

**Visual Traits:**
- Holographic stickers or seals
- Authentication tags or stamps
- Signatures (autographs)
- Serial numbers or edition numbers
- "Limited Edition" markings
- Vintage dates (especially 1990s or earlier)
- Protective cases or sleeves (cards, figures)
- Original packaging from collectible brands
- Team logos (Cubs, Yankees, Lakers, etc.)
- Character artwork (Pokemon, Star Wars, etc.)

**Examples that ARE collectibles:**
- Baseball card in protective case → collectible = TRUE
- Chicago Cubs jacket with MLB logo → collectible = TRUE
- Pokemon card (even common) → collectible = TRUE
- Vintage M&M tin → collectible = TRUE
- Star Wars action figure → collectible = TRUE
- Autographed photo → collectible = TRUE
- Hot Wheels in package → collectible = TRUE

**Examples that are NOT collectibles:**
- Plain white t-shirt → collectible = FALSE
- Generic coffee mug → collectible = FALSE
- Standard kitchen knife → collectible = FALSE
- Modern mass-produced clothing → collectible = FALSE

🎯 OUTPUT FORMAT

You MUST respond with ONLY valid JSON (no markdown, no explanations):

{
  "item_name": "1999 Pokemon Charizard Trading Card",
  "brand": "Pokemon",
  "franchise": "Pokemon",
  "category": "trading_cards",
  "description": "Holographic Charizard card from the 1999 Base Set, appears to be in protective sleeve.",
  "collectible": true,
  "collectible_confidence": 0.95,
  "collectible_indicators": [
    "Pokemon franchise",
    "Trading card in protective case",
    "Holographic card",
    "Vintage (1999)",
    "Charizard is highly collectible"
  ],
  "estimated_value_low": 50,
  "estimated_value_high": 500,
  "detected_keywords": ["pokemon", "charizard", "holographic", "1999", "base set"],
  "sku_upc": "",
  "logos_marks": ["Pokemon logo", "Nintendo copyright"],
  "condition": "good",
  "color": "multi-color",
  "size": "standard card",
  "material": "cardstock",
  "suggested_title": "1999 Pokemon Charizard Holographic Card - Base Set",
  "suggested_price": 150
}

OR if NOT a collectible:

{
  "item_name": "Blue Cotton T-Shirt",
  "brand": "Hanes",
  "franchise": "",
  "category": "apparel",
  "description": "Plain blue cotton t-shirt, appears to be size large.",
  "collectible": false,
  "collectible_confidence": 0.1,
  "collectible_indicators": [],
  "estimated_value_low": 5,
  "estimated_value_high": 15,
  "detected_keywords": ["t-shirt", "blue", "cotton"],
  "sku_upc": "",
  "logos_marks": ["Hanes tag"],
  "condition": "good",
  "color": "blue",
  "size": "L",
  "material": "cotton",
  "suggested_title": "Blue Hanes Cotton T-Shirt - Size L",
  "suggested_price": 10
}

IMPORTANT:
- Be AGGRESSIVE about marking collectibles
- If you see a sports logo, it's probably collectible
- If you see a franchise character, it's probably collectible
- If you see a trading card, it's DEFINITELY collectible
- When in doubt, mark collectible = true (deep analysis will verify)
- Respond with ONLY JSON, no other text
"""

        # Build request
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    *image_parts
                ]
            }],
            "generationConfig": {
                "temperature": 0.4,  # Lower temp for more consistent classification
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            }
        }

        try:
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                # Extract text from Gemini response
                try:
                    content_text = result["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError) as e:
                    return {
                        "error": f"Unexpected Gemini response structure: {str(e)}",
                        "raw_response": result
                    }

                # Parse JSON response
                try:
                    # Clean up any markdown formatting
                    if "```json" in content_text:
                        content_text = content_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in content_text:
                        content_text = content_text.split("```")[1].split("```")[0].strip()

                    analysis = json.loads(content_text)
                    analysis["ai_provider"] = "gemini"
                    return analysis

                except json.JSONDecodeError as e:
                    return {
                        "error": f"JSON parse error: {str(e)}",
                        "raw_response": content_text
                    }

            else:
                return {
                    "error": f"Gemini API error ({response.status_code}): {response.text[:500]}"
                }

        except Exception as e:
            return {
                "error": f"Exception: {str(e)}"
            }

    @classmethod
    def from_env(cls) -> "GeminiClassifier":
        """Create classifier from environment variables"""
        return cls()


# Convenience function
def classify_item(photos: List[Photo]) -> Dict[str, Any]:
    """
    Quick function to classify an item using Gemini.

    Args:
        photos: List of Photo objects

    Returns:
        Classification dict with item details and collectible flag
    """
    classifier = GeminiClassifier.from_env()
    return classifier.analyze_item(photos)
