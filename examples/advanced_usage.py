"""
Advanced Usage Example
======================
Shows advanced features:
- Creating listings with detailed item specifics
- AI enhancement before publishing
- Publishing to individual platforms
- Custom category and SEO data
"""

import os
from dotenv import load_dotenv

from src.schema import (
    UnifiedListing,
    Photo,
    Price,
    Shipping,
    Category,
    ItemSpecifics,
    SEOData,
    ListingCondition,
    ShippingService,
)
from src.publisher import CrossPlatformPublisher
from src.enhancer import AIEnhancer

# Load environment variables
load_dotenv()


def create_detailed_listing():
    """Create a listing with comprehensive details"""

    # Build item specifics
    item_specifics = ItemSpecifics(
        brand="Nike",
        size="10",
        color="Black/Red",
        model="Air Jordan 1",
        style="High Top",
    )

    # Set category
    category = Category(
        primary="Clothing, Shoes & Accessories",
        subcategory="Men's Shoes",
        suggested_keywords=["sneakers", "basketball", "retro", "jordan"],
    )

    # Set SEO data
    seo_data = SEOData(
        keywords=["nike", "air jordan", "sneakers", "retro", "vintage"],
        hashtags=["sneakers", "nike", "jordan", "sneakerhead"],
    )

    # Create listing with photos
    photos = [
        Photo(
            url="https://example.com/photo1.jpg",
            local_path="./photos/jordan_front.jpg",
            order=0,
            is_primary=True,
        ),
        Photo(
            url="https://example.com/photo2.jpg",
            local_path="./photos/jordan_side.jpg",
            order=1,
        ),
        Photo(
            url="https://example.com/photo3.jpg",
            local_path="./photos/jordan_sole.jpg",
            order=2,
        ),
    ]

    listing = UnifiedListing(
        title="Nike Air Jordan 1 Retro High OG Black/Red Size 10",
        description="""Classic Nike Air Jordan 1 in the iconic Black/Red colorway.

These sneakers are in excellent condition with minimal wear. The leather is
supple with no creasing or cracking. All original branding intact.

Includes:
- Original box
- Extra laces
- Authentication card

Perfect for collectors or anyone wanting to add a piece of sneaker history
to their collection.""",
        price=Price(
            amount=150.00,
            compare_at_price=200.00,
            minimum_acceptable=130.00,
        ),
        condition=ListingCondition.EXCELLENT,
        photos=photos,
        item_specifics=item_specifics,
        category=category,
        seo_data=seo_data,
        shipping=Shipping(
            service=ShippingService.STANDARD,
            cost=10.00,
            handling_time_days=2,
        ),
        sku="NIKE-AJ1-BLK-RED-10",
        returns_accepted=True,
        return_period_days=30,
    )

    return listing


def main():
    """Advanced publishing workflow"""

    print("🚀 Advanced Publishing Example\n")

    # Create listing
    print("📝 Creating detailed listing...")
    listing = create_detailed_listing()

    # Validate listing
    is_valid, errors = listing.validate()
    if not is_valid:
        print(f"❌ Listing validation failed: {errors}")
        return

    print("✅ Listing validated successfully\n")

    # Initialize publisher
    print("🔧 Initializing publisher...")
    publisher = CrossPlatformPublisher.from_env(auto_enhance=False)

    # Manually enhance with AI
    if publisher.ai_enhancer:
        print("🤖 Enhancing listing with AI...")
        listing = publisher.enhance_listing(listing, target_platform="general")
        print(f"   Enhanced title: {listing.title}")
        print(f"   AI provider: {listing.ai_provider}")
        print()

    # Publish to eBay only
    print("📤 Publishing to eBay...")
    ebay_result = publisher.publish_to_ebay(listing, enhance=False)

    if ebay_result.success:
        print(f"✅ eBay: Published successfully!")
        print(f"   Listing ID: {ebay_result.listing_id}")
    else:
        print(f"❌ eBay: Failed - {ebay_result.error}")

    print()

    # Publish to Mercari only
    print("📤 Publishing to Mercari...")
    mercari_result = publisher.publish_to_mercari(listing, enhance=False)

    if mercari_result.success:
        print(f"✅ Mercari: Published successfully!")
        print(f"   Listing ID: {mercari_result.listing_id}")
        if mercari_result.listing_url:
            print(f"   URL: {mercari_result.listing_url}")
    else:
        print(f"❌ Mercari: Failed - {mercari_result.error}")

    print()

    # Show publishing history
    print("📊 Publishing History:")
    for entry in publisher.get_publish_history():
        status = "✅" if entry["success"] else "❌"
        print(f"   {status} {entry['platform']}: {entry['listing_title']}")

    print()
    print(f"📈 Success Rate: {publisher.get_success_rate():.1f}%")


if __name__ == "__main__":
    main()
