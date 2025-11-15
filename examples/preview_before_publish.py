"""
Preview Before Publishing Example
=================================
Shows how to preview listings on each platform before publishing,
and confirm fields are properly filled.
"""

import os
from dotenv import load_dotenv

from src.schema import (
    UnifiedListing,
    Photo,
    Price,
    Shipping,
    ItemSpecifics,
    ListingCondition,
)
from src.publisher import (
    CrossPlatformPublisher,
    ListingPreviewer,
    confirm_publish,
)

# Load environment variables
load_dotenv()


def main():
    """Preview and confirm before publishing"""

    print("🎨 Preview & Confirmation Example\n")

    # Create a listing
    listing = UnifiedListing(
        title="Nike Air Jordan 1 Retro High OG Black Red Size 10 Authentic",
        description="""Classic Nike Air Jordan 1 in the iconic Black/Red "Bred" colorway.

These sneakers are in excellent condition with minimal wear. The leather is
supple with no creasing or cracking. All original branding intact including
Nike swoosh and Wings logo.

Includes:
- Original box
- Extra red laces
- Authentication card from StockX

Perfect for collectors or anyone wanting to add a piece of sneaker history
to their collection. Ships within 1 business day via USPS Priority Mail.""",
        price=Price(
            amount=150.00,
            compare_at_price=200.00,
        ),
        condition=ListingCondition.EXCELLENT,
        photos=[
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
        ],
        item_specifics=ItemSpecifics(
            brand="Nike",
            size="10",
            color="Black/Red",
            model="Air Jordan 1",
            style="High Top",
        ),
        shipping=Shipping(
            cost=10.00,
            handling_time_days=1,
        ),
        sku="NIKE-AJ1-BRED-10",
    )

    # Option 1: Manual preview
    print("="*70)
    print("OPTION 1: Manual Preview")
    print("="*70)

    previewer = ListingPreviewer()

    # Preview for eBay
    ebay_preview = previewer.preview_for_ebay(listing)
    print(f"\n📊 eBay Preview:")
    print(f"  Title: {ebay_preview['title']}")
    print(f"  Length: {ebay_preview['title_length']}")
    print(f"  Price: {ebay_preview['price']}")
    print(f"  Photos: {ebay_preview['photos']}/{ebay_preview['photo_limit']}")

    if ebay_preview['issues']:
        print(f"\n  ⚠️  Issues:")
        for issue in ebay_preview['issues']:
            print(f"    {issue}")

    # Preview for Mercari
    mercari_preview = previewer.preview_for_mercari(listing)
    print(f"\n📊 Mercari Preview:")
    print(f"  Title: {mercari_preview['title']}")
    print(f"  Length: {mercari_preview['title_length']}")
    print(f"  Price: {mercari_preview['price']}")
    print(f"  Photos: {mercari_preview['photos']}/{mercari_preview['photo_limit']}")

    if mercari_preview['issues']:
        print(f"\n  ⚠️  Issues:")
        for issue in mercari_preview['issues']:
            print(f"    {issue}")

    # Option 2: Interactive confirmation
    print("\n\n" + "="*70)
    print("OPTION 2: Interactive Confirmation")
    print("="*70)

    if confirm_publish(listing, platforms=["eBay", "Mercari"]):
        print("\n✅ User confirmed - proceeding with publish...")

        # Initialize publisher
        publisher = CrossPlatformPublisher.from_env()

        # Publish to all platforms
        results = publisher.publish_to_all(listing)

        # Show results
        print("\n📤 Publishing Results:")
        for platform, result in results.items():
            if result.success:
                print(f"  ✅ {platform}: {result.listing_id}")
            else:
                print(f"  ❌ {platform}: {result.error}")
    else:
        print("\n❌ User cancelled - no listings published")

    # Option 3: Pretty print preview
    print("\n\n" + "="*70)
    print("OPTION 3: Pretty Print Preview")
    print("="*70)

    previewer.print_preview(listing)


if __name__ == "__main__":
    main()
