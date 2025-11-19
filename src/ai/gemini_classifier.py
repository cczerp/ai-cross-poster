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
- **CARD DETECTION** - Identifies trading cards & sports cards
- **CARD CLASSIFICATION** - Extracts card-specific details

Claude handles deep collectible analysis (authentication, grading, variants).
"""

import os
import base64
import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests

from ..schema.unified_listing import Photo


class GeminiClassifier:
    """
    Fast item classifier using Google Gemini.

    This is designed for speed and cost-efficiency.
    Use for initial classification before deep collectible analysis.
    Now includes specialized card detection and classification.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini classifier"""
        # Check multiple env var names (including common typo GEMENI_API_KEY)
        self.api_key = (
            api_key or
            os.getenv("GOOGLE_AI_API_KEY") or
            os.getenv("GEMINI_API_KEY") or
            os.getenv("GEMENI_API_KEY")  # Common typo
        )
        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY, GEMINI_API_KEY, or GEMENI_API_KEY must be set")

        # Use Gemini 2.5 Flash for speed and cost-efficiency
        # Current image-capable models (v1 API endpoint):
        # - gemini-2.5-flash (DEFAULT - fastest, cheapest, great for classification)
        # - gemini-2.5-pro (better quality, more expensive)
        # - gemini-2.0-flash (older but still supported)
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        # Use v1 endpoint for Gemini models
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

        # Retry logic for rate limits (exponential backoff)
        max_retries = 4
        base_delay = 2  # seconds

        for attempt in range(max_retries):
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

                # Handle rate limit errors (429) with exponential backoff
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # 2s, 4s, 8s, 16s
                        print(f"Gemini rate limit hit. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        return {
                            "error": "Gemini API is currently overloaded. Please wait 60 seconds and try again. This is due to free tier rate limits.",
                            "error_type": "rate_limit",
                            "retry_after": 60
                        }

                # Handle other API errors
                else:
                    error_msg = response.text[:500]

                    # Provide user-friendly error messages
                    if response.status_code == 400:
                        return {
                            "error": "Invalid request to Gemini API. Please check your photos are valid images.",
                            "error_type": "bad_request",
                            "details": error_msg
                        }
                    elif response.status_code == 403:
                        return {
                            "error": "Gemini API key is invalid or doesn't have access. Please check your GEMINI_API_KEY in .env file.",
                            "error_type": "auth_error",
                            "details": error_msg
                        }
                    elif response.status_code >= 500:
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            print(f"Gemini server error. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(delay)
                            continue
                        else:
                            return {
                                "error": "Gemini API is experiencing server issues. Please try again in a few minutes.",
                                "error_type": "server_error",
                                "details": error_msg
                            }
                    else:
                        return {
                            "error": f"Gemini API error ({response.status_code}): {error_msg}",
                            "error_type": "unknown"
                        }

            except requests.Timeout:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"Request timeout. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    return {
                        "error": "Request to Gemini API timed out after multiple attempts. Please check your internet connection.",
                        "error_type": "timeout"
                    }

            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"Exception occurred: {str(e)}. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    return {
                        "error": f"Error communicating with Gemini API: {str(e)}",
                        "error_type": "exception"
                    }

        # Should never reach here, but just in case
        return {
            "error": "Failed after maximum retries",
            "error_type": "max_retries_exceeded"
        }

    def analyze_card(self, photos: List[Photo]) -> Dict[str, Any]:
        """
        Specialized card analysis using Gemini Vision.

        Extracts card-specific details for:
        - Trading Card Games (Pokémon, MTG, Yu-Gi-Oh, etc.)
        - Sports Cards (NFL, NBA, MLB, NHL, etc.)

        Returns:
            {
                "is_card": bool,
                "card_type": str,  # 'pokemon', 'mtg', 'yugioh', 'sports_nfl', etc.
                "card_name": str,
                "player_name": str,  # For sports cards
                "card_number": str,
                "set_name": str,
                "set_code": str,
                "year": int,
                "brand": str,  # Topps, Panini, etc. (sports cards)
                "series": str,  # Prizm, Chrome, etc. (sports cards)
                "rarity": str,
                "is_rookie_card": bool,
                "is_autographed": bool,
                "is_graded": bool,
                "grading_company": str,  # PSA, BGS, CGC
                "grading_score": float,
                "parallel": str,  # Silver, Gold, etc.
                "condition": str,
                "estimated_value_low": float,
                "estimated_value_high": float,
                "confidence": float,
            }
        """
        if not photos:
            return {"error": "No photos provided", "is_card": False}

        # Prepare images
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

        # Card-specific analysis prompt
        prompt = """Analyze this image and determine if it's a trading card or sports card.

🎴 CARD DETECTION & CLASSIFICATION

**Step 1: Is this a card?**
Look for:
- Standard card dimensions (roughly 2.5" x 3.5")
- Card in protective sleeve, top loader, or grading case
- Visible card features (borders, text, stats)
- Trading card game elements (energy symbols, mana costs, etc.)
- Sports card elements (player photo, team logo, stats on back)

**Step 2: What type of card?**

TRADING CARD GAMES:
- Pokemon: Look for Pokemon logo, energy symbols, HP, attacks
- Magic: The Gathering (MTG): Look for mana symbols, card types, expansion symbols
- Yu-Gi-Oh!: Look for ATK/DEF numbers, card types (Monster/Spell/Trap)
- One Piece, Dragon Ball, etc.

SPORTS CARDS:
- NFL: Football players, team logos, NFL shield
- NBA: Basketball players, team logos, NBA logo
- MLB: Baseball players, team logos, MLB logo
- NHL: Hockey players, team logos, NHL logo
- Soccer: Players, team crests, league logos

**Step 3: Extract Details**

For TCG Cards:
- Card name (at top of card)
- Set symbol (bottom right, or expansion mark)
- Card number (usually bottom: "12/102" format)
- Rarity (star, circle, diamond, or text like "Rare", "Ultra Rare")
- Set name if visible

For Sports Cards:
- Player name
- Year (usually on front or back)
- Brand (Topps, Panini, Upper Deck, Donruss, Fleer, Bowman)
- Series (Prizm, Chrome, Optic, Select, etc.)
- Card number
- Rookie Card designation ("RC" logo or text)
- Parallel/variant (Silver, Gold, Refractor, etc.)
- Team and position

**Step 4: Grading & Condition**

Check for:
- PSA, BGS, CGC grading case (plastic slab)
- Grading score (1-10 scale)
- Serial number on case
- If ungraded: estimate condition (Mint, Near Mint, Excellent, Good, Poor)

**Step 5: Special Features**

- Autograph (signature on card)
- Rookie card (RC designation)
- Limited edition / numbered (e.g., "5/99")
- Holographic / foil finish
- Insert set designation

**Step 6: Value Estimation**

Provide rough market value based on:
- Player/character popularity
- Card rarity
- Condition/grade
- Year (vintage vs modern)
- Market demand

OUTPUT FORMAT (JSON only, no markdown):

For a CARD:
{
  "is_card": true,
  "card_type": "pokemon",
  "card_name": "Charizard",
  "player_name": "",
  "card_number": "4/102",
  "set_name": "Base Set",
  "set_code": "BS",
  "year": 1999,
  "brand": "",
  "series": "",
  "rarity": "Rare Holo",
  "is_rookie_card": false,
  "is_autographed": false,
  "is_graded": true,
  "grading_company": "PSA",
  "grading_score": 9.0,
  "parallel": "",
  "condition": "Mint",
  "estimated_value_low": 2000,
  "estimated_value_high": 5000,
  "confidence": 0.95
}

For a SPORTS CARD:
{
  "is_card": true,
  "card_type": "sports_nfl",
  "card_name": "Tom Brady Rookie Card",
  "player_name": "Tom Brady",
  "card_number": "236",
  "set_name": "2000 Playoff Contenders",
  "set_code": "",
  "year": 2000,
  "brand": "Playoff",
  "series": "Contenders",
  "rarity": "Rookie Ticket Autograph",
  "is_rookie_card": true,
  "is_autographed": true,
  "is_graded": true,
  "grading_company": "PSA",
  "grading_score": 10.0,
  "parallel": "",
  "condition": "Gem Mint",
  "estimated_value_low": 100000,
  "estimated_value_high": 500000,
  "confidence": 0.98
}

For NOT A CARD:
{
  "is_card": false,
  "confidence": 0.95
}

Analyze the image(s) now and respond with ONLY the JSON."""

        # Combine text + images
        content = [{"text": prompt}]
        content.extend(image_parts)

        payload = {
            "contents": [{
                "parts": content
            }],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for factual extraction
                "maxOutputTokens": 1024,
            }
        }

        try:
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content_text = result['candidates'][0]['content']['parts'][0]['text']

                # Parse JSON response
                content_text = content_text.strip()
                if content_text.startswith('```json'):
                    content_text = content_text[7:-3].strip()
                elif content_text.startswith('```'):
                    content_text = content_text[3:-3].strip()

                card_data = json.loads(content_text)
                return card_data

            else:
                return {
                    "error": f"Gemini API error: {response.status_code}",
                    "is_card": False
                }

        except Exception as e:
            return {
                "error": f"Card analysis failed: {str(e)}",
                "is_card": False
            }

    @classmethod
    def from_env(cls) -> "GeminiClassifier":
        """Create classifier from environment variables"""
        return cls()


# Convenience functions
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


def analyze_card(photos: List[Photo]) -> Dict[str, Any]:
    """
    Quick function to analyze a card using Gemini.
    
    Args:
        photos: List of Photo objects
        
    Returns:
        Card analysis dict with card-specific details
    """
    classifier = GeminiClassifier.from_env()
    return classifier.analyze_card(photos)


def smart_analyze(photos: List[Photo]) -> Dict[str, Any]:
    """
    Smart analyzer that detects item type and routes appropriately.
    
    First does quick card detection, then:
    - If card: run detailed card analysis
    - If not card: run standard item classification
    
    Args:
        photos: List of Photo objects
        
    Returns:
        Analysis dict with appropriate details
    """
    classifier = GeminiClassifier.from_env()
    
    # Try card analysis first (faster than full classification)
    card_result = classifier.analyze_card(photos)
    
    if card_result.get('is_card'):
        # It's a card! Return card-specific data
        return {
            **card_result,
            'analysis_type': 'card'
        }
    else:
        # Not a card, do standard classification
        item_result = classifier.analyze_item(photos)
        return {
            **item_result,
            'analysis_type': 'item'
        }
