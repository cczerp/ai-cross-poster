"""
Detailed Attribute Detection
=============================
Detects specific item attributes: type, size, color, material, etc.
"""

import os
import base64
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests

from ..schema.unified_listing import Photo


class AttributeDetector:
    """
    AI-powered detailed attribute detection.

    Identifies:
    - Item type (shirt, pants, socks, shoes, jacket, etc.)
    - Size (S/M/L/XL, numeric sizes, etc.)
    - Color (primary and secondary colors)
    - Material (cotton, polyester, leather, etc.)
    - Brand and model
    - Condition details
    - Style/fit (slim, regular, oversized, etc.)
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        """Initialize attribute detector"""
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

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

    def detect_attributes_claude(
        self,
        photos: List[Photo]
    ) -> Dict[str, Any]:
        """
        Detect detailed item attributes using Claude.
        """
        if not self.anthropic_api_key:
            return {"error": "No Anthropic API key"}

        # Prepare images
        image_contents = []
        for photo in photos[:4]:
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

        prompt = """Analyze these images and provide DETAILED item attributes.

Identify:

**1. Item Type/Category:**
   - Main category (clothing, shoes, accessories, electronics, collectibles, etc.)
   - Specific type (t-shirt, jeans, sneakers, hoodie, jacket, etc.)
   - Subcategory if applicable

**2. Size Information:**
   - Size (XS/S/M/L/XL/XXL or numeric like 32x34, 8.5, etc.)
   - Fit (slim, regular, oversized, athletic, etc.)
   - Measurements if visible

**3. Color Details:**
   - Primary color
   - Secondary colors
   - Pattern (solid, striped, plaid, floral, etc.)
   - Color code/name if identifiable

**4. Brand & Model:**
   - Brand name
   - Model/style name
   - Collection/line
   - Season/year if identifiable

**5. Material & Composition:**
   - Primary material (cotton, polyester, leather, etc.)
   - Fabric blend if visible
   - Material quality indicators

**6. Condition Assessment:**
   - Overall condition (new, like new, excellent, good, fair, poor)
   - Specific issues (stains, holes, fading, etc.)
   - Wear patterns
   - Missing parts/accessories

**7. Special Features:**
   - Tags (price tags, brand tags, size tags)
   - Special features (pockets, zippers, buttons, etc.)
   - Technology features (for electronics)
   - Authentication markers

**8. Target Gender/Age:**
   - Men's, Women's, Unisex, Kids
   - Age group if applicable

**9. Style & Aesthetics:**
   - Style (casual, formal, athletic, streetwear, vintage, etc.)
   - Design elements
   - Era/decade (for vintage items)

**10. Retail Information:**
   - Original retail price if visible
   - Current market value estimate
   - Comparable items

Format as JSON:
```json
{
  "item_type": {
    "main_category": "clothing",
    "specific_type": "t-shirt",
    "subcategory": "graphic tee"
  },
  "size": {
    "size": "L",
    "fit": "regular",
    "measurements": {
      "chest": "22 inches",
      "length": "29 inches"
    }
  },
  "color": {
    "primary": "black",
    "secondary": ["white"],
    "pattern": "graphic print",
    "description": "Black with white logo"
  },
  "brand": {
    "name": "Nike",
    "model": "Sportswear",
    "collection": "2024 Spring",
    "verified": true
  },
  "material": {
    "primary": "cotton",
    "composition": "100% Cotton",
    "quality": "premium"
  },
  "condition": {
    "overall": "excellent",
    "specific_issues": [],
    "wear_notes": "Minimal wear",
    "has_tags": true,
    "tag_info": "Original tags attached"
  },
  "features": {
    "special": ["crew neck", "short sleeves", "screen printed logo"],
    "technology": null
  },
  "target_demographic": {
    "gender": "unisex",
    "age_group": "adult"
  },
  "style": {
    "style_type": "casual athletic",
    "era": "modern",
    "aesthetic": "sporty"
  },
  "retail_info": {
    "original_price": 35,
    "estimated_current_value": 25,
    "market_notes": "Standard Nike tee, good resale demand"
  },
  "confidence": {
    "overall": 0.95,
    "brand_confidence": 0.98,
    "size_confidence": 1.0,
    "condition_confidence": 0.90
  }
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

        # Try using the latest Sonnet model - fallback to specific version if needed
        model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

        payload = {
            "model": model,
            "max_tokens": 2500,
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

                try:
                    if "```json" in content_text:
                        content_text = content_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in content_text:
                        content_text = content_text.split("```")[1].split("```")[0].strip()

                    attributes = json.loads(content_text)
                    attributes["ai_provider"] = "claude"
                    return attributes

                except json.JSONDecodeError as e:
                    return {"error": f"JSON parse error: {str(e)}", "raw": content_text}
            else:
                # Show detailed error including status code
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", response.text)
                    return {"error": f"Claude API error ({response.status_code}): {error_msg}"}
                except:
                    return {"error": f"Claude API error ({response.status_code}): {response.text[:500]}"}

        except Exception as e:
            return {"error": f"Exception: {str(e)}"}

    def detect_attributes_openai(
        self,
        photos: List[Photo]
    ) -> Dict[str, Any]:
        """
        Fallback: Detect attributes with GPT-4 Vision.
        """
        if not self.openai_api_key:
            return {"error": "No OpenAI API key"}

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

        prompt = """Analyze this item and provide detailed attributes in JSON format: item type, size, color, brand, material, condition, features, target demographic, style, and retail info."""

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

                    attributes = json.loads(content)
                    attributes["ai_provider"] = "gpt4"
                    return attributes

                except json.JSONDecodeError:
                    return {"error": "JSON parse error", "raw": content}
            else:
                return {"error": f"OpenAI error: {response.text}"}

        except Exception as e:
            return {"error": f"Exception: {str(e)}"}

    def detect(
        self,
        photos: List[Photo],
        force_gpt4: bool = False
    ) -> Dict[str, Any]:
        """
        Main method: Detect all attributes using AI.

        Returns detailed attribute dictionary.
        """
        if not force_gpt4:
            print("🔍 Detecting attributes with Claude...")
            attributes = self.detect_attributes_claude(photos)

            # Check if successful
            if "error" not in attributes:
                print("✅ Attributes detected successfully")
                return attributes

            print(f"⚠️  Claude failed: {attributes.get('error')}")

        # Fallback to GPT-4
        print("🔄 Trying GPT-4 Vision...")
        attributes = self.detect_attributes_openai(photos)

        if "error" not in attributes:
            print("✅ Attributes detected with GPT-4")
        else:
            print(f"❌ GPT-4 failed: {attributes.get('error')}")

        return attributes

    @classmethod
    def from_env(cls) -> "AttributeDetector":
        """Create detector from environment variables"""
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )


# Convenience function
def detect_attributes(
    photos: List[Photo],
    force_gpt4: bool = False
) -> Dict[str, Any]:
    """
    Quick function to detect item attributes.

    Args:
        photos: List of Photo objects
        force_gpt4: Force use of GPT-4 Vision

    Returns:
        Dictionary with detailed attributes
    """
    detector = AttributeDetector.from_env()
    return detector.detect(photos, force_gpt4)
