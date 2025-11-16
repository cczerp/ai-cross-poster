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
        prompt = """Analyze these images to determine if this is a COLLECTIBLE item.

IMPORTANT: Trading cards and sports cards are ALWAYS collectibles, even common ones.

Collectibles include:
- Trading cards (sports cards - baseball, basketball, football, hockey, soccer, Pokemon, Magic, Yu-Gi-Oh, etc.)
  * Even if in a protective case or sleeve, these are collectibles
  * Look for player names, card brands (Topps, Panini, Upper Deck, etc.)
  * Check for rookie cards, autographs, special editions
- Action figures and toys (vintage, limited edition)
- Coins and currency
- Stamps
- Comic books
- Video games (especially sealed, rare, or retro)
- Vintage clothing/streetwear (Supreme, vintage Nike, concert tees, etc.)
- Vinyl records
- Movie/sports memorabilia
- Antiques and vintage items
- Limited edition sneakers
- Designer items (vintage Gucci, Louis Vuitton, etc.)
- Collectible books (first editions, signed)

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
   - Recent selling prices if you know them
   - Market trend (increasing, stable, decreasing)

6. **Key Attributes:**
   - Specific identifiers (serial numbers, edition, variant)
   - Condition details
   - Completeness (box, packaging, accessories)

7. **Authentication Notes:**
   - How to verify authenticity
   - Red flags or concerns

8. **Additional Info:**
   - Why is this valuable/collectible?
   - What collectors look for
   - Best platforms to sell on

Format as JSON:
```json
{
  "is_collectible": true/false,
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
    "red_flags": ["Check for reseals", "Verify holo authenticity"]
  },
  "why_valuable": "First edition Charizard is one of the most iconic Pokemon cards",
  "what_collectors_want": "PSA graded, shadowless, centering",
  "best_platforms": ["eBay", "PWCC", "Heritage Auctions"],
  "reasoning": "Identified by distinctive Base Set artwork, 1st edition stamp visible"
}
```

If NOT a collectible, return:
```json
{
  "is_collectible": false,
  "confidence_score": 0.9,
  "item_type": "regular clothing",
  "reasoning": "Standard mass-produced item with no collectible value"
}
```
"""

        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        content = [{"type": "text", "text": prompt}]
        content.extend(image_contents)

        # Use Claude Sonnet for collectible identification (needs better accuracy)
        # Haiku struggles with identifying collectibles accurately
        # This is worth the extra cost since collectible ID is critical
        model = os.getenv("CLAUDE_COLLECTIBLE_MODEL", "claude-3-sonnet-20240229")

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
                    # Extract JSON from markdown code blocks if present
                    if "```json" in content_text:
                        content_text = content_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in content_text:
                        content_text = content_text.split("```")[1].split("```")[0].strip()

                    analysis = json.loads(content_text)
                    analysis["ai_provider"] = "claude"
                    return analysis

                except json.JSONDecodeError as e:
                    return {
                        "is_collectible": False,
                        "error": f"JSON parse error: {str(e)}",
                        "raw_response": content_text
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
