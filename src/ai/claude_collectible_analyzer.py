"""
Claude-based Deep Collectible Analysis
========================================
Uses Claude AI for detailed collectible authentication, grading, and valuation.

This is triggered AFTER Gemini detects a collectible item.
Claude provides:
- Authentication markers and verification
- Professional grading assessment
- Rarity and variant detection
- Historical significance
- Detailed condition analysis
- Market value analysis
- Fraud detection red flags
"""

import os
import base64
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests

from ..schema.unified_listing import Photo


class ClaudeCollectibleAnalyzer:
    """
    Deep collectible analyzer using Claude AI (Anthropic).

    This provides detailed authentication and grading information
    for collectible items that Gemini has flagged.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Claude analyzer"""
        self.api_key = (
            api_key or
            os.getenv("ANTHROPIC_API_KEY") or
            os.getenv("CLAUDE_API_KEY")
        )
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY or CLAUDE_API_KEY must be set")

        # Use Claude 3.5 Sonnet for best quality
        self.model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.api_url = "https://api.anthropic.com/v1/messages"

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

    def deep_analyze_collectible(
        self,
        photos: List[Photo],
        basic_analysis: Dict[str, Any],
        db=None
    ) -> Dict[str, Any]:
        """
        Deep collectible analysis using Claude.

        Args:
            photos: List of Photo objects
            basic_analysis: The Gemini analysis results (provides context)

        Returns:
            {
                "authentication": {
                    "is_authentic": bool,
                    "confidence": float,
                    "authentication_markers": List[str],
                    "red_flags": List[str],
                    "verification_notes": str
                },
                "grading": {
                    "overall_grade": str,  # e.g., "PSA 9", "CGC 8.5", "Mint"
                    "centering": str,
                    "corners": str,
                    "edges": str,
                    "surface": str,
                    "grading_notes": str
                },
                "rarity": {
                    "rarity_level": str,  # Common, Uncommon, Rare, Ultra Rare, etc.
                    "print_run": str,
                    "variants": List[str],
                    "edition": str,
                    "rarity_notes": str
                },
                "market_analysis": {
                    "current_market_value_low": float,
                    "current_market_value_high": float,
                    "recent_sales": List[Dict],
                    "market_trend": str,  # Rising, Stable, Declining
                    "demand_level": str,  # High, Medium, Low
                    "market_notes": str
                },
                "historical_context": {
                    "release_year": int,
                    "manufacturer": str,
                    "series": str,
                    "significance": str,
                    "historical_notes": str
                },
                "condition_details": {
                    "wear_and_tear": str,
                    "damage": List[str],
                    "modifications": List[str],
                    "completeness": str,
                    "original_packaging": bool,
                    "condition_notes": str
                },
                "recommendations": {
                    "suggested_listing_price": float,
                    "best_platforms": List[str],
                    "target_buyers": str,
                    "selling_tips": List[str],
                    "preservation_tips": List[str]
                },
                "fraud_check": {
                    "concerns": List[str],
                    "verification_needed": bool,
                    "third_party_grading_recommended": bool
                }
            }
        """
        if not photos:
            return {"error": "No photos provided"}

        # Prepare images for Claude
        image_parts = []
        for photo in photos[:4]:  # Claude supports multiple images
            if photo.local_path:
                image_b64 = self._encode_image_to_base64(photo.local_path)
                mime_type = self._get_image_mime_type(photo.local_path)
                image_parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": image_b64
                    }
                })

        # Build comprehensive analysis prompt
        item_name = basic_analysis.get('item_name', 'collectible item')
        brand = basic_analysis.get('brand', '')
        franchise = basic_analysis.get('franchise', '')
        category = basic_analysis.get('category', '')

        # RAG: Search for similar collectibles in database
        rag_context = ""
        if db:
            try:
                similar_items = db.find_similar_collectibles(
                    brand=brand if brand else None,
                    franchise=franchise if franchise else None,
                    category=category if category else None,
                    limit=5
                )

                if similar_items:
                    rag_context = "\n\n**KNOWLEDGE BASE (Similar items analyzed before):**\n"
                    for idx, item in enumerate(similar_items, 1):
                        rag_context += f"\n{idx}. {item.get('name', 'Unknown')}"
                        if item.get('deep_analysis'):
                            try:
                                analysis = json.loads(item['deep_analysis'])
                                # Extract key insights
                                if 'market_analysis' in analysis:
                                    ma = analysis['market_analysis']
                                    rag_context += f"\n   - Market value: ${ma.get('current_market_value_low', 0)}-${ma.get('current_market_value_high', 0)}"
                                    rag_context += f"\n   - Trend: {ma.get('market_trend', 'Unknown')}"
                                if 'authentication' in analysis:
                                    auth = analysis['authentication']
                                    if auth.get('authentication_markers'):
                                        rag_context += f"\n   - Auth markers: {', '.join(auth['authentication_markers'][:3])}"
                                if 'grading' in analysis:
                                    grade = analysis['grading']
                                    rag_context += f"\n   - Typical grade: {grade.get('overall_grade', 'N/A')}"
                            except:
                                pass
                        rag_context += f"\n   - Times found: {item.get('times_found', 1)}"
                        rag_context += "\n"
            except Exception as e:
                # RAG is optional, don't fail if it doesn't work
                print(f"RAG search failed: {e}")

        prompt = f"""You are an expert collectibles appraiser and authenticator with decades of experience.

I need you to perform a DEEP ANALYSIS of this collectible item for authentication, grading, and valuation purposes.

**BASIC INFORMATION (from initial scan):**
- Item: {item_name}
- Brand: {brand}
- Franchise: {franchise}
- Category: {category}
{rag_context}

**YOUR TASK:**

Please analyze these images thoroughly and provide a COMPREHENSIVE assessment.

IMPORTANT: If similar items are listed in the "KNOWLEDGE BASE" above, use that information to inform your analysis - especially for market values, authentication markers, and typical conditions. This is real data from previously analyzed items.

Your assessment should cover:

1. **AUTHENTICATION**
   - Is this item authentic or potentially counterfeit?
   - What authentication markers do you see (holograms, stamps, serial numbers, etc.)?
   - Any red flags or concerns about authenticity?
   - Confidence level in authentication

2. **GRADING** (use relevant grading standards - PSA for cards, CGC for comics, etc.)
   - Overall condition grade
   - Centering (if applicable)
   - Corner condition
   - Edge condition
   - Surface condition
   - Any notable defects or wear

3. **RARITY & VARIANTS**
   - How rare is this item?
   - What edition/print run is this from?
   - Are there different variants? Which variant is this?
   - Any special markings or features?

4. **MARKET ANALYSIS**
   - Current market value range (low/high)
   - Recent sales data (if you're aware of typical prices)
   - Market trend (rising/stable/declining)
   - Demand level
   - Best selling season/timing

5. **HISTORICAL CONTEXT**
   - Release year
   - Manufacturer/publisher
   - Series/set name
   - Historical significance
   - Why collectors value this

6. **CONDITION DETAILS**
   - Specific wear and tear observations
   - Any damage (creases, stains, scratches, etc.)
   - Modifications or restoration
   - Completeness (all parts present?)
   - Original packaging present?

7. **SELLING RECOMMENDATIONS**
   - Suggested listing price
   - Best platforms to sell on (eBay, COMC, Heritage, etc.)
   - Target buyer demographic
   - Tips to maximize sale price
   - Preservation/storage recommendations

8. **FRAUD CHECK**
   - Any concerns about authenticity?
   - Should seller get third-party grading/authentication?
   - Known counterfeits of this item to watch for

**OUTPUT FORMAT:**

You MUST respond with ONLY valid JSON (no markdown, no explanations). Use this exact structure:

{{
  "authentication": {{
    "is_authentic": true,
    "confidence": 0.95,
    "authentication_markers": ["Holographic stamp", "Serial number matches format", "Correct font and spacing"],
    "red_flags": [],
    "verification_notes": "All visible authentication markers appear correct. Hologram is genuine."
  }},
  "grading": {{
    "overall_grade": "PSA 9 equivalent (Mint)",
    "centering": "Excellent (90/10 or better)",
    "corners": "Sharp with minimal wear",
    "edges": "Clean with no visible chipping",
    "surface": "Near-perfect with one minor print line",
    "grading_notes": "Card is in excellent condition with only minor flaws preventing a perfect grade."
  }},
  "rarity": {{
    "rarity_level": "Ultra Rare",
    "print_run": "Limited first edition",
    "variants": ["1st Edition Shadowless", "Unlimited", "Shadowless"],
    "edition": "1st Edition Shadowless",
    "rarity_notes": "This is from the highly sought-after first print run."
  }},
  "market_analysis": {{
    "current_market_value_low": 150,
    "current_market_value_high": 350,
    "recent_sales": [
      {{"platform": "eBay", "price": 250, "date": "2024-11", "grade": "PSA 9"}},
      {{"platform": "Heritage", "price": 325, "date": "2024-10", "grade": "PSA 9"}}
    ],
    "market_trend": "Rising",
    "demand_level": "High",
    "market_notes": "Prices have increased 15% in the last 6 months due to renewed interest."
  }},
  "historical_context": {{
    "release_year": 1999,
    "manufacturer": "Wizards of the Coast",
    "series": "Pokemon Base Set 1st Edition",
    "significance": "One of the most iconic cards from the original Pokemon TCG release",
    "historical_notes": "Part of the Pokemon craze that defined late 90s collecting culture."
  }},
  "condition_details": {{
    "wear_and_tear": "Minimal edge wear on top left corner",
    "damage": ["Very minor print line visible on surface"],
    "modifications": [],
    "completeness": "Complete",
    "original_packaging": false,
    "condition_notes": "Card appears to have been well-preserved in a sleeve since new."
  }},
  "recommendations": {{
    "suggested_listing_price": 275,
    "best_platforms": ["eBay", "COMC", "TCGPlayer", "Facebook collector groups"],
    "target_buyers": "Serious Pokemon collectors, especially those focusing on 1st edition cards",
    "selling_tips": [
      "Consider getting PSA graded to confirm condition and increase value",
      "List during peak buying season (holiday season)",
      "Include detailed close-up photos of all corners and surface",
      "Mention it has been stored in protective sleeve"
    ],
    "preservation_tips": [
      "Keep in penny sleeve + top loader",
      "Store in climate-controlled environment",
      "Avoid direct sunlight",
      "Do not remove from sleeve unnecessarily"
    ]
  }},
  "fraud_check": {{
    "concerns": [],
    "verification_needed": false,
    "third_party_grading_recommended": true,
    "notes": "While authentication markers look good, professional grading would increase buyer confidence and potentially value."
  }}
}}

IMPORTANT GUIDELINES:
- Be thorough but honest - if you can't determine something from the images, say so
- Use industry-standard grading terminology
- Provide realistic market values based on your knowledge
- Highlight any concerns that could affect value or authenticity
- Be specific about what you see in the photos
- If this is outside your expertise, indicate uncertainty in your confidence scores
"""

        # Prepare API request
        content = image_parts + [{"type": "text", "text": prompt}]

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ]
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()

            # Extract the text content
            if "content" in result and len(result["content"]) > 0:
                text_content = result["content"][0]["text"]

                # Parse JSON from response
                # Claude might wrap JSON in markdown code blocks, so clean it
                text_content = text_content.strip()
                if text_content.startswith("```json"):
                    text_content = text_content[7:]
                if text_content.startswith("```"):
                    text_content = text_content[3:]
                if text_content.endswith("```"):
                    text_content = text_content[:-3]
                text_content = text_content.strip()

                analysis = json.loads(text_content)
                return analysis
            else:
                return {"error": "No content in Claude response"}

        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}"}
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse JSON response: {str(e)}"}
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    @classmethod
    def from_env(cls):
        """Create analyzer from environment variables"""
        return cls()
