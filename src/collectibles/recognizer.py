"""
Collectible Recognition Module
===============================
Uses AI to identify collectibles, pull pricing data, and store in database.
"""

import os
import base64
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import requests

from ..schema.unified_listing import Photo, UnifiedListing
from ..database import get_db


class CollectibleRecognizer:
    """
    AI-powered collectible recognition and pricing system.

    Uses Claude as primary analyzer (cost-efficient) with GPT-4 Vision fallback.
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        """Initialize collectible recognizer"""
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.db = get_db()

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

    def analyze_for_collectibles_claude(
        self,
        photos: List[Photo]
    ) -> Dict[str, Any]:
        """
        Analyze photos using Claude to identify if item is a collectible.

        Returns detailed information about the collectible including:
        - Is it a collectible?
        - Category (toys, cards, coins, stamps, vintage clothing, etc.)
        - Brand, model, year
        - Estimated market value
        - Key attributes
        - Confidence score
        """
        if not self.anthropic_api_key:
            return {"is_collectible": False, "error": "No Anthropic API key"}

        # Prepare images
        image_contents = []
        for photo in photos[:4]:  # Limit to 4 photos
            image_dict = {"type": "image"}

            if photo.local_path:
                image_b64 = self._encode_image_to_base64(photo.local_path)
                mime_type = self._get_image_mime_type(photo.local_path)
                image_dict["source"] = {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": image_b64,
                }
            elif photo.url:
                image_dict["source"] = {
                    "type": "url",
                    "url": photo.url,
                }

            image_contents.append(image_dict)

        # Build comprehensive collectibles analysis prompt
        prompt = """🔍 EXPERT COLLECTIBLE AUTHENTICATION & GRADING

You are an expert collectibles authenticator and grader. Your job is to:
1. Verify if this is a genuine collectible
2. Authenticate it (check for counterfeits)
3. Identify the specific variant
4. Grade the condition
5. Assess market value

⚠️ CRITICAL DETECTION RULES:
- ANY trading card (sports, Pokemon, Magic, etc.) = COLLECTIBLE (even commons!)
- ANY item with official sports team logos (MLB, NBA, NFL, NHL, etc.) = COLLECTIBLE
- ANY team names (Cubs, Yankees, Lakers, etc.) = COLLECTIBLE
- Cards in protective cases/sleeves = COLLECTIBLE
- Vintage sports apparel/jerseys = COLLECTIBLE
- Autographed items = COLLECTIBLE

🔍 AUTHENTICATION CHECKLIST:

For Trading Cards:
- Check for authentic holo pattern (not printed-on)
- Verify copyright dates and trademarks
- Look for edition stamps (1st Edition, Shadowless, etc.)
- Check card stock quality and thickness
- Examine border consistency and centering
- Look for print lines or color bleeds (signs of counterfeits)
- Verify set symbols and card numbers
- **SIGNATURE AUTHENTICATION** (CRITICAL):
  * Real vs Stamped/Printed Signatures:
    - REAL signatures: Ink bleeds into card stock, varies in thickness, has depth
    - FAKE signatures: Perfectly uniform, no bleeding, flat/printed appearance
    - Look for pen pressure variation (heavier at start, lighter at end)
    - Check for natural flow and imperfections (real signatures aren't perfect)
  * Ink Analysis:
    - Real: Ink pooling, feathering, slight bleeding at edges
    - Fake: Sharp edges, no bleeding, looks like it was printed
    - Check if ink sits ON TOP of card vs absorbed INTO card
  * Placement & Style:
    - Where is signature located? (Some players always sign in specific spots)
    - Size and boldness (some players sign small, others large)
    - Angle and flow (natural hand movement vs stamped straight)
    - Consistency with known examples of this player's signature
  * Red Flags:
    - Perfect uniformity = likely stamped/printed
    - No ink variation = fake
    - Signature looks too neat = suspicious
    - Wrong placement for this player = fake
    - No evidence of pen pressure = printed
  * Confidence Scoring:
    - HIGH confidence real: Ink bleeding, pressure variation, natural flow, correct placement
    - MEDIUM confidence: Some indicators but unclear from photo
    - LOW confidence real / HIGH confidence fake: Perfect uniformity, no bleeding, wrong style

For Sports Memorabilia:
- Verify official team logos (stitching, colors, placement)
- Check tags and labels (brand, size, care instructions)
- Look for authentication holograms or certificates
- Examine stitching quality (official vs bootleg)
- Check jersey numbers and player names
- Verify era-appropriate details

For Toys/Figures:
- Check for official brand markings
- Verify packaging authenticity
- Look for production stamps and dates
- Check paint quality and mold details
- Verify accessories and completeness

🎯 VARIANT IDENTIFICATION:

Identify specific variant details:
- Edition (1st Edition, Limited, Special, etc.)
- Print run or production year
- Color variations
- Factory errors (valuable!)
- Regional differences
- Packaging variations
- Special features (holo, foil, embossed, etc.)

📊 CONDITION GRADING (be detailed):

Grade based on:
- Corners: Sharp, slightly worn, rounded, damaged
- Edges: Clean, whitening, chipping, peeling
- Surface: Pristine, minor scratches, creases, stains
- Centering: Perfectly centered, off-center, badly off-center
- Overall cleanliness
- Original packaging condition

Grading scale:
- Gem Mint (10): Perfect, no flaws
- Mint (9-9.5): Nearly perfect, minor manufacturing flaws only
- Near Mint (7-8.5): Excellent, minimal wear
- Excellent (6-6.5): Light wear, still great
- Good (4-5.5): Noticeable wear but complete
- Fair (2-3.5): Heavy wear, possible damage
- Poor (1): Severe damage

⚠️ CRITICAL: You MUST respond with ONLY valid JSON. No explanations, no markdown formatting, no other text.
Start your response with { and end with }. Do not wrap in ```json blocks.

Provide detailed analysis:

1. **Is this a collectible?** (yes/no)
2. **Confidence Score** (0.0 to 1.0)
3. **Category** (toys, cards, coins, stamps, vintage_clothing, video_games, etc.)
4. **Item Details:**
   - Name/Title
   - Brand/Manufacturer
   - Model/Edition
   - Year/Era
   - Condition assessment
   - Rarity (common, uncommon, rare, very rare, ultra rare)

5. **Market Value Estimation:**
   - Estimated Low ($)
   - Estimated High ($)
   - **3 REASONS for this price estimate** (REQUIRED):
     * Explain exactly why this item is worth this price
     * Include signature authenticity if autographed (e.g., "Real signature adds $X value" or "Fake signature means card-only value")
     * Include rarity, condition, demand factors
     * Be specific (e.g., "Rookie card of Hall of Famer", "1st Edition rare variant", "Mint condition increases value 3x")
   - Recent selling prices if you know them
   - Market trend (increasing, stable, decreasing)

6. **Key Attributes:**
   - Specific identifiers (serial numbers, edition, variant)
   - Condition details
   - Completeness (box, packaging, accessories)

7. **Authentication Notes:**
   - How to verify authenticity
   - Red flags or concerns
   - **Signature Authentication** (if autographed):
     * Is signature real or stamped/printed?
     * Signature authenticity confidence (0.0 to 1.0)
     * Ink characteristics (bleeding, pressure, depth)
     * Placement and style analysis
     * Comparison to known authentic examples
     * Red flags identified

8. **Additional Info:**
   - Why is this valuable/collectible?
   - What collectors look for
   - Best platforms to sell on

Response format (respond with ONLY this JSON, no markdown):
{
  "is_collectible": true,
  "confidence_score": 0.95,
  "category": "trading_cards",
  "name": "Pokemon Charizard 1st Edition",
  "brand": "Pokemon",
  "model": "Charizard Base Set",
  "year": 1999,
  "condition": "Near Mint",
  "rarity": "ultra rare",
  "estimated_value_low": 5000,
  "estimated_value_high": 15000,
  "price_reasons": [
    "1st Edition Charizard from Base Set is the most iconic Pokemon card, highly sought after by collectors worldwide",
    "Near Mint condition significantly increases value - PSA 8-9 grade cards sell for $8,000-$12,000",
    "Holographic variant with shadowless printing increases rarity and collector demand"
  ],
  "market_trend": "increasing",
  "recent_sales": [
    {"price": 8000, "condition": "PSA 8", "date": "2024-01"},
    {"price": 12000, "condition": "PSA 9", "date": "2024-02"}
  ],
  "attributes": {
    "edition": "1st Edition",
    "set": "Base Set",
    "card_number": "4/102",
    "has_shadowless": true,
    "graded": false
  },
  "authentication": {
    "key_identifiers": ["1st edition stamp", "copyright date", "holo pattern"],
    "red_flags": ["Check for reseals", "Verify holo authenticity"],
    "has_signature": false,
    "signature_analysis": null
  },
  "why_valuable": "First edition Charizard is one of the most iconic Pokemon cards",
  "what_collectors_want": "PSA graded, shadowless, centering",
  "best_platforms": ["eBay", "PWCC", "Heritage Auctions"],
  "reasoning": "Identified by distinctive Base Set artwork, 1st edition stamp visible"
}

Example with AUTOGRAPH (include signature in price_reasons):
{
  "is_collectible": true,
  "confidence_score": 0.85,
  "category": "trading_cards",
  "name": "Michael Jordan Signed Rookie Card",
  "brand": "Upper Deck",
  "year": 1986,
  "condition": "Near Mint",
  "rarity": "ultra rare",
  "estimated_value_low": 5000,
  "estimated_value_high": 15000,
  "price_reasons": [
    "Michael Jordan rookie card is one of the most valuable basketball cards - unsigned versions sell for $500-$1,500",
    "AUTHENTIC SIGNATURE adds $3,500-$13,500 in value - signature shows ink bleeding, pressure variation, and correct placement (lower right corner) matching known MJ autographs",
    "Near Mint condition with PSA/JSA certification potential could push this to $15,000+ at auction"
  ],
  "authentication": {
    "key_identifiers": ["Upper Deck hologram", "card stock quality", "signature placement"],
    "red_flags": ["Verify signature authenticity with PSA/JSA"],
    "has_signature": true,
    "signature_analysis": {
      "is_authentic": true,
      "confidence": 0.8,
      "authenticity_reasoning": "Signature shows natural ink bleeding into card stock, pressure variation visible in strokes, placement consistent with known MJ autographs (lower right corner). Flow appears natural and matches authenticated examples.",
      "ink_characteristics": {
        "bleeding": "Visible ink feathering at edges - consistent with real Sharpie on card stock",
        "pressure_variation": "Noticeable thickness changes in signature strokes - indicates hand pressure",
        "depth": "Ink appears absorbed into card surface, not sitting on top"
      },
      "placement_style": {
        "location": "Lower right corner",
        "typical_for_player": true,
        "size": "Medium-large (consistent with Jordan's known signing style)",
        "angle": "Slight upward angle - natural hand movement"
      },
      "red_flags_found": [],
      "authenticity_indicators": [
        "Ink bleeding into card stock",
        "Pressure variation in strokes",
        "Correct placement for this player",
        "Natural flow and imperfections",
        "Matches known Jordan signature examples"
      ],
      "recommendation": "HIGH confidence authentic. Recommend PSA/JSA certification for maximum value."
    }
  },
  "reasoning": "Autographed rookie card with strong signature authenticity indicators"
}

Example with FAKE/STAMPED signature (include fake_indicators):
{
  "is_collectible": true,
  "confidence_score": 0.95,
  "category": "trading_cards",
  "name": "Derek Jeter Card with Stamped Signature",
  "brand": "Topps",
  "year": 2010,
  "condition": "Near Mint",
  "rarity": "common",
  "estimated_value_low": 5,
  "estimated_value_high": 15,
  "price_reasons": [
    "This is a mass-produced 2010 Topps card - common print run means low base value ($3-$10)",
    "FAKE/STAMPED SIGNATURE adds NO value - signature is printed facsimile, not hand-signed (perfect uniformity, no ink bleeding)",
    "Card is valued for the card itself only, not as an autograph. Real Jeter autograph would be $200-$500"
  ],
  "fake_indicators": [
    "Signature shows perfect uniformity in all strokes - real signatures have natural variation from hand pressure",
    "No ink bleeding or feathering at edges - printed signatures have sharp edges, real ink bleeds into card stock",
    "Signature is perfectly horizontal in center - unnatural placement, Jeter typically signs at angle in lower right"
  ],
  "authentication": {
    "key_identifiers": ["Topps logo", "card number"],
    "red_flags": ["Signature is stamped/printed, not hand-signed"],
    "has_signature": true,
    "signature_analysis": {
      "is_authentic": false,
      "confidence": 0.95,
      "authenticity_reasoning": "Signature shows clear signs of being stamped/printed rather than hand-signed. Perfect uniformity in all strokes, no ink bleeding, sharp edges indicate printing process. This is a facsimile signature common on mass-produced cards.",
      "ink_characteristics": {
        "bleeding": "None - sharp edges indicate printed signature",
        "pressure_variation": "None - perfectly uniform thickness throughout",
        "depth": "Flat appearance - ink sits on surface, not absorbed"
      },
      "placement_style": {
        "location": "Center of card",
        "typical_for_player": false,
        "size": "Perfectly consistent across multiple cards",
        "angle": "Perfectly horizontal - unnatural for hand signing"
      },
      "red_flags_found": [
        "Perfect uniformity in all strokes",
        "No ink bleeding or feathering",
        "Sharp edges - printed appearance",
        "No evidence of pen pressure variation",
        "Too perfect - real signatures have imperfections"
      ],
      "authenticity_indicators": [],
      "recommendation": "This is a STAMPED/PRINTED facsimile signature. Value is for the card only, not the autograph. Worth $5-15, not autograph pricing."
    }
  },
  "reasoning": "Card has printed facsimile signature, not hand-signed autograph"
}

If NOT a collectible, return:
{
  "is_collectible": false,
  "confidence_score": 0.9,
  "item_type": "regular clothing",
  "reasoning": "Standard mass-produced item with no collectible value"
}

REMEMBER: Respond with ONLY the JSON object. No other text before or after.
"""

        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        content = [{"type": "text", "text": prompt}]
        content.extend(image_contents)

        # Use Claude Haiku for collectible identification
        # Sonnet would be better but isn't available on all API tiers (causes 404)
        # The aggressive prompt rules help Haiku identify sports collectibles better
        model = os.getenv("CLAUDE_COLLECTIBLE_MODEL", "claude-3-haiku-20240307")

        payload = {
            "model": model,
            "max_tokens": 3000,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
        }

        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                content_text = result["content"][0]["text"]

                # Parse JSON response
                try:
                    # Debug: Check if content_text is empty first
                    if not content_text or content_text.strip() == "":
                        return {
                            "is_collectible": False,
                            "error": "Claude returned empty response",
                            "raw_response": f"Full API response: {result}",
                            "debug_info": "content_text was empty"
                        }

                    # Extract JSON from markdown code blocks if present
                    if "```json" in content_text:
                        content_text = content_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in content_text:
                        content_text = content_text.split("```")[1].split("```")[0].strip()

                    # Remove any leading/trailing whitespace or text before/after JSON
                    content_text = content_text.strip()

                    # Try to find JSON object if there's extra text
                    if not content_text.startswith("{"):
                        # Try to find the start of JSON
                        start_idx = content_text.find("{")
                        if start_idx != -1:
                            content_text = content_text[start_idx:]

                    if not content_text.endswith("}"):
                        # Try to find the end of JSON
                        end_idx = content_text.rfind("}")
                        if end_idx != -1:
                            content_text = content_text[:end_idx + 1]

                    analysis = json.loads(content_text)
                    analysis["ai_provider"] = "claude"
                    return analysis

                except json.JSONDecodeError as e:
                    return {
                        "is_collectible": False,
                        "error": f"JSON parse error: {str(e)}",
                        "raw_response": content_text[:1000] if content_text else "EMPTY RESPONSE",
                        "debug_info": f"Response length: {len(content_text) if content_text else 0} chars"
                    }
            else:
                # Show detailed error including status code
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", response.text)
                    return {
                        "is_collectible": False,
                        "error": f"Claude API error ({response.status_code}): {error_msg}"
                    }
                except:
                    return {
                        "is_collectible": False,
                        "error": f"Claude API error ({response.status_code}): {response.text[:500]}"
                    }

        except Exception as e:
            return {
                "is_collectible": False,
                "error": f"Exception: {str(e)}"
            }

    def analyze_for_collectibles_openai(
        self,
        photos: List[Photo]
    ) -> Dict[str, Any]:
        """
        Fallback: Analyze with GPT-4 Vision if Claude fails.
        """
        if not self.openai_api_key:
            return {"is_collectible": False, "error": "No OpenAI API key"}

        # Prepare images
        image_contents = []
        for photo in photos[:4]:
            if photo.local_path:
                image_b64 = self._encode_image_to_base64(photo.local_path)
                mime_type = self._get_image_mime_type(photo.local_path)
                image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_b64}"
                    }
                })
            elif photo.url:
                image_contents.append({
                    "type": "image_url",
                    "image_url": {"url": photo.url}
                })

        prompt = """Analyze if this is a collectible item. Provide detailed JSON analysis of collectibility, value, and market data. Include is_collectible (bool), confidence_score, category, name, brand, estimated values, and reasoning."""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *image_contents,
                ]
            }
        ]

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "gpt-4o",
            "messages": messages,
            "max_tokens": 2000,
        }

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                try:
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()

                    analysis = json.loads(content)
                    analysis["ai_provider"] = "gpt4"
                    return analysis

                except json.JSONDecodeError:
                    return {"is_collectible": False, "error": "JSON parse error", "raw": content}
            else:
                return {"is_collectible": False, "error": f"OpenAI error: {response.text}"}

        except Exception as e:
            return {"is_collectible": False, "error": f"Exception: {str(e)}"}

    def identify_and_store(
        self,
        photos: List[Photo],
        force_gpt4: bool = False
    ) -> Tuple[bool, Optional[int], Dict[str, Any]]:
        """
        Main method: Identify if item is collectible and store in database.

        Returns:
            (is_collectible, collectible_id, analysis_data)
        """
        # Step 1: Try Claude first (unless force_gpt4)
        analysis = {}

        if not force_gpt4:
            print("🔍 Analyzing with Claude to identify collectible...")
            analysis = self.analyze_for_collectibles_claude(photos)

        # Step 2: Fallback to GPT-4 if Claude failed or force_gpt4
        if force_gpt4 or not analysis.get("is_collectible"):
            if not force_gpt4:
                print("🔄 Claude didn't identify as collectible, trying GPT-4 Vision...")
            else:
                print("🔍 Analyzing with GPT-4 Vision...")

            gpt_analysis = self.analyze_for_collectibles_openai(photos)

            # Merge analyses if both ran
            if analysis:
                analysis["gpt4_fallback"] = gpt_analysis
                # Trust GPT-4 if it says it's collectible
                if gpt_analysis.get("is_collectible"):
                    analysis = gpt_analysis
            else:
                analysis = gpt_analysis

        # Step 3: Check if it's a collectible
        if not analysis.get("is_collectible"):
            print("❌ Not identified as a collectible")
            return (False, None, analysis)

        print(f"✅ Collectible identified: {analysis.get('name', 'Unknown')}")
        print(f"   Category: {analysis.get('category', 'Unknown')}")
        print(f"   Estimated Value: ${analysis.get('estimated_value_low', 0)} - ${analysis.get('estimated_value_high', 0)}")
        print(f"   Confidence: {analysis.get('confidence_score', 0):.0%}")

        # Step 4: Check if we've seen this collectible before
        existing = self.db.find_collectible(
            name=analysis.get("name", ""),
            brand=analysis.get("brand")
        )

        if existing:
            print(f"💾 Found existing collectible in database (ID: {existing['id']})")
            collectible_id = existing["id"]
            # Increment found counter
            self.db.increment_collectible_found(collectible_id)
        else:
            # Step 5: Add to database
            print("💾 Adding new collectible to database...")

            # Extract image URLs
            image_urls = []
            for photo in photos:
                if photo.url:
                    image_urls.append(photo.url)
                elif photo.local_path:
                    image_urls.append(photo.local_path)

            collectible_id = self.db.add_collectible(
                name=analysis.get("name", "Unknown Collectible"),
                category=analysis.get("category"),
                brand=analysis.get("brand"),
                model=analysis.get("model"),
                year=analysis.get("year"),
                condition=analysis.get("condition"),
                estimated_value_low=analysis.get("estimated_value_low"),
                estimated_value_high=analysis.get("estimated_value_high"),
                market_data={
                    "recent_sales": analysis.get("recent_sales", []),
                    "market_trend": analysis.get("market_trend", "stable"),
                    "best_platforms": analysis.get("best_platforms", []),
                },
                attributes=analysis.get("attributes", {}),
                image_urls=image_urls,
                identified_by=analysis.get("ai_provider", "claude"),
                confidence_score=analysis.get("confidence_score", 0.0),
                notes=analysis.get("reasoning", ""),
            )

            print(f"✅ Collectible saved to database (ID: {collectible_id})")

        return (True, collectible_id, analysis)

    @classmethod
    def from_env(cls) -> "CollectibleRecognizer":
        """Create recognizer from environment variables"""
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )


# Convenience function
def identify_collectible(
    photos: List[Photo],
    force_gpt4: bool = False
) -> Tuple[bool, Optional[int], Dict[str, Any]]:
    """
    Quick function to identify and store collectible.

    Args:
        photos: List of Photo objects
        force_gpt4: Force use of GPT-4 Vision (skip Claude)

    Returns:
        (is_collectible, collectible_id, analysis_data)
    """
    recognizer = CollectibleRecognizer.from_env()
    return recognizer.identify_and_store(photos, force_gpt4)
