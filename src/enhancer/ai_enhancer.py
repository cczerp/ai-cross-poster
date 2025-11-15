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
    Dual-AI enhancer using both Anthropic Claude and OpenAI.

    Strategy:
    - Step 1: Claude analyzes photos and creates initial listing (details, SEO, keywords)
    - Step 2: GPT-4 Vision verifies and refines to ensure label and description accuracy
    - Combined: Best of both for maximum listing quality
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

    def verify_with_gpt4_vision(self, photos: List[Photo], claude_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify and refine listing using GPT-4 Vision (Step 2).
        Double-checks Claude's analysis to ensure accuracy of label and description.

        Args:
            photos: List of photos to verify
            claude_data: Initial data from Claude analysis

        Returns:
            Dictionary with verified/refined data
        """
        if not self.use_openai:
            return claude_data

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

        # Build verification prompt with Claude's initial data
        prompt = f"""Review these product images and verify the following listing details created by another AI.

**Current Title**: {claude_data.get('title', 'N/A')}
**Current Description**: {claude_data.get('description', 'N/A')}
**Suggested Keywords**: {', '.join(claude_data.get('keywords', []))}
**Category**: {claude_data.get('category', 'N/A')}
**Brand/Model**: {claude_data.get('brand', 'N/A')} / {claude_data.get('model', 'N/A')}

Your task: Verify accuracy and refine if needed. Focus on:
1. Is the title accurate and optimized?
2. Is the description factually correct based on what you see?
3. Are there any missing important details?
4. Any corrections needed for brand, model, or specifics?

Provide refined/corrected data as JSON:
{{
  "title": "...",
  "description": "...",
  "keywords": ["...", "..."],
  "category": "...",
  "brand": "...",
  "model": "...",
  "corrections_made": ["list any corrections"],
  "verified": true
}}"""

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
            "temperature": 0.3,  # Lower temperature for verification accuracy
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

                verified_data = json.loads(content)

                # Merge verified data with original claude_data (keep search_terms from Claude if not provided)
                final_data = {**claude_data, **verified_data}

                return final_data
            except json.JSONDecodeError:
                # If parsing fails, return Claude's data as-is
                return claude_data
        else:
            # If API call fails, return Claude's data
            print(f"GPT-4 Vision verification failed: {response.text}")
            return claude_data


    def enhance_listing(
        self,
        listing: UnifiedListing,
        target_platform: str = "general",
        force: bool = False,
    ) -> UnifiedListing:
        """
        Complete AI enhancement workflow with two-step process.

        Step 1: Claude analyzes photos and creates initial listing
        Step 2: GPT-4 Vision verifies and refines for accuracy

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

        # Step 1: Claude analyzes photos first (initial comprehensive analysis)
        claude_analysis = {}
        if self.use_anthropic and listing.photos:
            try:
                print("🤖 Step 1: Claude analyzing photos...")
                claude_analysis = self.analyze_photos_claude(listing.photos, target_platform)
            except Exception as e:
                print(f"❌ Claude analysis failed: {e}")

        # Step 2: GPT-4 Vision verifies and refines Claude's analysis
        final_data = claude_analysis
        if self.use_openai and listing.photos and claude_analysis:
            try:
                print("🔍 Step 2: GPT-4 Vision verifying accuracy...")
                final_data = self.verify_with_gpt4_vision(listing.photos, claude_analysis)
            except Exception as e:
                print(f"⚠️  GPT-4 Vision verification failed (using Claude data): {e}")
                final_data = claude_analysis

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

            # Track which AI providers were used (Claude first, then GPT-4)
            providers = []
            if self.use_anthropic:
                providers.append("Claude (analysis)")
            if self.use_openai:
                providers.append("GPT-4 Vision (verification)")
            listing.ai_provider = " → ".join(providers)

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
