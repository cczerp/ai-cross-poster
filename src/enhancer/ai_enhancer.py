"""
Dual-AI Listing Enhancer
=========================
Uses both OpenAI and Anthropic Claude to enhance listings with:
- AI-generated descriptions
- Title optimization
- Photo analysis
- Keyword extraction
- Category suggestions
"""

import os
import base64
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import requests
from pathlib import Path

from ..schema.unified_listing import (
    UnifiedListing,
    Photo,
    SEOData,
    Category,
    ItemSpecifics,
)


class AIEnhancer:
    """
    Dual-AI enhancer with cost-efficient fallback strategy.

    Strategy (Cost-Optimized):
    - Step 1: Claude analyzes photos (primary analyzer)
    - Step 2: Only use GPT-4 Vision as fallback if Claude can't identify the item
    - This saves costs by avoiding double analysis on every photo

    Claude handles ~90% of listings successfully, so GPT-4 is rarely needed.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        use_openai: bool = True,
        use_anthropic: bool = True,
    ):
        """
        Initialize AI enhancer.

        Args:
            openai_api_key: OpenAI API key
            anthropic_api_key: Anthropic API key
            use_openai: Enable OpenAI enhancement
            use_anthropic: Enable Anthropic enhancement
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.use_openai = use_openai and self.openai_api_key is not None
        self.use_anthropic = use_anthropic and self.anthropic_api_key is not None

        if not (self.use_openai or self.use_anthropic):
            raise ValueError(
                "At least one AI provider must be enabled with valid API key"
            )

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

    def analyze_photos_claude(self, photos: List[Photo], target_platform: str = "general") -> Dict[str, Any]:
        """
        Initial photo analysis using Claude Vision (Step 1).
        Creates comprehensive listing with details, SEO, and keywords.

        Args:
            photos: List of photos to analyze
            target_platform: Target platform for optimization

        Returns:
            Dictionary with initial analysis, title, description, keywords, etc.
        """
        if not self.use_anthropic:
            return {}

        # Prepare images for vision analysis
        image_contents = []
        for photo in photos[:4]:  # Limit to 4 photos to save tokens
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

        # Platform-specific context
        platform_context = {
            "ebay": "eBay (focus on detailed specs, trust-building language, and search keywords)",
            "mercari": "Mercari (casual, mobile-friendly, highlight condition and value)",
            "general": "general e-commerce",
        }
        context = platform_context.get(target_platform.lower(), "general e-commerce")

        # Build comprehensive analysis prompt
        prompt = f"""Analyze these product images and create a comprehensive listing for {context}.

Provide:
1. **Item Title**: Compelling, keyword-rich title (under 80 characters)
2. **Detailed Description**: 2-3 paragraphs covering features, condition, and value proposition
3. **SEO Keywords**: 15-20 relevant search keywords
4. **Search Terms**: Alternative phrases buyers might use
5. **Category**: Suggested category (e.g., "Electronics > Cameras")
6. **Item Specifics**: Brand, model, size, color, material if visible
7. **Condition Notes**: Specific observations about condition
8. **Key Features**: Bullet points of notable selling points

Format as JSON:
{{
  "title": "...",
  "description": "...",
  "keywords": ["...", "..."],
  "search_terms": ["...", "..."],
  "category": "...",
  "brand": "...",
  "model": "...",
  "color": "...",
  "condition_notes": "...",
  "features": ["...", "..."]
}}"""

        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        # Build message with images
        content = [{"type": "text", "text": prompt}]
        content.extend(image_contents)

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
        }

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )

        if response.status_code == 200:
            result = response.json()
            content_text = result["content"][0]["text"]

            # Parse JSON response
            import json
            try:
                if "```json" in content_text:
                    content_text = content_text.split("```json")[1].split("```")[0].strip()
                elif "```" in content_text:
                    content_text = content_text.split("```")[1].split("```")[0].strip()

                analysis = json.loads(content_text)
                return analysis
            except json.JSONDecodeError:
                return {"raw_response": content_text}
        else:
            raise Exception(f"Claude API error: {response.text}")

    def analyze_photos_openai_fallback(self, photos: List[Photo]) -> Dict[str, Any]:
        """
        Analyze photos using GPT-4 Vision as fallback (when Claude fails).
        Does a fresh analysis from scratch.

        Args:
            photos: List of photos to analyze

        Returns:
            Dictionary with photo analysis, suggested title, description, keywords
        """
        if not self.use_openai:
            return {}

        # Prepare images for vision analysis
        image_contents = []
        for photo in photos[:4]:  # Limit to 4 photos to save tokens
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

        # Build prompt for fresh analysis
        prompt = """Analyze these product images and provide comprehensive listing details.

Provide:
1. **Item Title**: Compelling, keyword-rich title (under 80 characters)
2. **Detailed Description**: 2-3 paragraphs covering features, condition, and value proposition
3. **SEO Keywords**: 15-20 relevant search keywords
4. **Search Terms**: Alternative phrases buyers might use
5. **Category**: Suggested category (e.g., "Electronics > Cameras")
6. **Item Specifics**: Brand, model, size, color, material if visible
7. **Condition Notes**: Specific observations about condition
8. **Key Features**: Bullet points of notable selling points

Format as JSON:
{
  "title": "...",
  "description": "...",
  "keywords": ["...", "..."],
  "search_terms": ["...", "..."],
  "category": "...",
  "brand": "...",
  "model": "...",
  "color": "...",
  "condition_notes": "...",
  "features": ["...", "..."]
}"""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *image_contents,
                ]
            }
        ]

        # Call OpenAI API
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "gpt-4o",  # GPT-4 Vision
            "messages": messages,
            "max_tokens": 1500,
            "temperature": 0.7,
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # Parse JSON response
            import json
            try:
                # Try to extract JSON from markdown code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                analysis = json.loads(content)
                return analysis
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {"raw_response": content}
        else:
            raise Exception(f"OpenAI API error: {response.text}")


    def _is_analysis_complete(self, analysis: Dict[str, Any]) -> bool:
        """
        Check if AI analysis successfully identified the item.

        Args:
            analysis: Analysis data from AI

        Returns:
            True if analysis has minimum required fields, False otherwise
        """
        # Check for essential fields that indicate successful identification
        has_title = bool(analysis.get("title")) and len(analysis.get("title", "")) > 10
        has_description = bool(analysis.get("description")) and len(analysis.get("description", "")) > 20
        has_category = bool(analysis.get("category"))

        return has_title and has_description and has_category

    def enhance_listing(
        self,
        listing: UnifiedListing,
        target_platform: str = "general",
        force: bool = False,
    ) -> UnifiedListing:
        """
        Complete AI enhancement workflow with cost-efficient fallback.

        Strategy:
        - Step 1: Claude analyzes photos (primary analyzer)
        - Step 2: If Claude can't identify the item, use GPT-4 Vision as fallback
        - This saves costs by only using GPT-4 when necessary

        Args:
            listing: UnifiedListing to enhance
            target_platform: Target platform for optimization
            force: Force re-enhancement even if already enhanced

        Returns:
            Enhanced UnifiedListing
        """
        if listing.ai_enhanced and not force:
            # Already enhanced, skip
            return listing

        final_data = {}
        ai_providers_used = []

        # Step 1: Claude analyzes photos first (primary analyzer)
        if self.use_anthropic and listing.photos:
            try:
                print("🤖 Claude analyzing photos...")
                claude_analysis = self.analyze_photos_claude(listing.photos, target_platform)

                # Check if Claude successfully identified the item
                if self._is_analysis_complete(claude_analysis):
                    print("✅ Claude successfully identified the item")
                    final_data = claude_analysis
                    ai_providers_used.append("Claude")
                else:
                    print("⚠️  Claude analysis incomplete - will try GPT-4 Vision as fallback")
                    # Keep Claude's partial data, may use as fallback
                    final_data = claude_analysis

            except Exception as e:
                print(f"❌ Claude analysis failed: {e}")

        # Step 2: Use GPT-4 Vision as fallback ONLY if Claude failed or couldn't identify
        if self.use_openai and listing.photos:
            # Only use GPT-4 if Claude didn't successfully complete the analysis
            if not self._is_analysis_complete(final_data):
                try:
                    print("🔄 Using GPT-4 Vision as fallback...")
                    # Use GPT-4 to analyze from scratch (not verify Claude's data)
                    gpt_analysis = self.analyze_photos_openai_fallback(listing.photos)

                    if self._is_analysis_complete(gpt_analysis):
                        print("✅ GPT-4 Vision successfully identified the item")
                        final_data = gpt_analysis
                        ai_providers_used.append("GPT-4 Vision (fallback)")
                    else:
                        # Merge partial results from both
                        final_data = {**final_data, **gpt_analysis}
                        ai_providers_used.append("GPT-4 Vision (fallback partial)")

                except Exception as e:
                    print(f"❌ GPT-4 Vision fallback failed: {e}")
                    # Continue with whatever data we have from Claude
            else:
                print("💰 Skipping GPT-4 Vision (Claude analysis was complete)")

        # Step 3: Apply enhancements to listing
        if final_data:
            # Update description if provided
            if final_data.get("description"):
                listing.description = final_data["description"]

            # Update title if provided
            if final_data.get("title"):
                listing.title = final_data["title"]

            # Update SEO data
            if final_data.get("keywords"):
                listing.seo_data.keywords = final_data["keywords"]

            if final_data.get("search_terms"):
                listing.seo_data.search_terms = final_data["search_terms"]

            # Update category if suggested
            if final_data.get("category"):
                category_parts = final_data["category"].split(" > ")
                if not listing.category:
                    listing.category = Category(
                        primary=category_parts[0],
                        subcategory=category_parts[1] if len(category_parts) > 1 else None,
                    )

            # Update item specifics if provided
            if final_data.get("brand"):
                listing.item_specifics.brand = final_data["brand"]
            if final_data.get("model"):
                listing.item_specifics.model = final_data["model"]
            if final_data.get("color"):
                listing.item_specifics.color = final_data["color"]

            # Mark as AI enhanced
            listing.ai_enhanced = True
            listing.ai_enhancement_timestamp = datetime.now()

            # Track which AI providers were actually used
            if ai_providers_used:
                listing.ai_provider = " → ".join(ai_providers_used)
            else:
                listing.ai_provider = "None (analysis failed)"

        return listing

    @classmethod
    def from_env(cls) -> "AIEnhancer":
        """
        Create enhancer from environment variables.

        Expected variables:
            - OPENAI_API_KEY (optional)
            - ANTHROPIC_API_KEY (optional)
        """
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        )


def enhance_listing(
    listing: UnifiedListing,
    target_platform: str = "general",
    force: bool = False,
) -> UnifiedListing:
    """
    Convenience function to enhance a listing.

    Args:
        listing: UnifiedListing to enhance
        target_platform: Target platform
        force: Force re-enhancement

    Returns:
        Enhanced listing
    """
    enhancer = AIEnhancer.from_env()
    return enhancer.enhance_listing(listing, target_platform, force)
