"""
AI Photo Analysis Example
=========================
Demonstrates using AI to analyze photos and automatically create listing content.
"""

import os
from dotenv import load_dotenv

from src.schema import (
    UnifiedListing,
    Photo,
    Price,
    ListingCondition,
    Shipping,
)
from src.enhancer import AIEnhancer
from src.publisher import publish_to_all

# Load environment variables
load_dotenv()


def create_listing_from_photos(photo_paths: list) -> UnifiedListing:
    """
    Create a listing by analyzing photos with AI.

    Args:
        photo_paths: List of local photo file paths

    Returns:
        UnifiedListing with AI-generated content
    """

    # Create photos list
    photos = [
        Photo(
            local_path=path,
            url=f"https://example.com/photo{i}.jpg",  # You'd upload these
            order=i,
            is_primary=(i == 0),
        )
        for i, path in enumerate(photo_paths)
    ]

    # Create minimal listing (AI will fill in the rest)
    listing = UnifiedListing(
        title="Item for sale",  # Placeholder - AI will improve
        description="Item description",  # Placeholder - AI will improve
        price=Price(amount=50.00),  # You still need to set price
        condition=ListingCondition.GOOD,  # You still need to set condition
        photos=photos,
        shipping=Shipping(cost=5.00),
    )

    return listing


def main():
    """Analyze photos and create listing"""

    print("📸 AI Photo Analysis Example\n")

    # Example photo paths (replace with your actual photos)
    photo_paths = [
        "./photos/item_front.jpg",
        "./photos/item_back.jpg",
        "./photos/item_detail.jpg",
    ]

    # Create basic listing from photos
    print("📝 Creating listing from photos...")
    listing = create_listing_from_photos(photo_paths)

    # Initialize AI enhancer
    print("🤖 Initializing AI enhancer...")
    enhancer = AIEnhancer.from_env()

    # Analyze photos and enhance listing
    print("🔍 Analyzing photos with AI...")
    enhanced_listing = enhancer.enhance_listing(
        listing,
        target_platform="general",
        force=True,
    )

    # Show results
    print("\n✨ AI Enhancement Results:\n")
    print(f"Title: {enhanced_listing.title}")
    print(f"\nDescription:\n{enhanced_listing.description}")
    print(f"\nKeywords: {', '.join(enhanced_listing.seo_data.keywords)}")

    if enhanced_listing.category:
        print(f"\nSuggested Category: {enhanced_listing.category.primary}")
        if enhanced_listing.category.subcategory:
            print(f"  > {enhanced_listing.category.subcategory}")

    print(f"\nAI Provider: {enhanced_listing.ai_provider}")
    print(f"Enhanced: {enhanced_listing.ai_enhanced}")

    # Ask if user wants to publish
    response = input("\n📤 Publish this listing? (y/n): ")

    if response.lower() == "y":
        print("\n📤 Publishing to all platforms...")
        results = publish_to_all(enhanced_listing)

        for platform, result in results.items():
            if result.success:
                print(f"✅ {platform}: Published!")
            else:
                print(f"❌ {platform}: {result.error}")
    else:
        print("\n👋 Publishing cancelled.")


if __name__ == "__main__":
    main()
