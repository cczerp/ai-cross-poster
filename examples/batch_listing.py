"""
Batch Listing Example
=====================
Create and publish multiple listings at once.
"""

import os
import time
from dotenv import load_dotenv
from pathlib import Path

from src.schema import (
    UnifiedListing,
    Photo,
    Price,
    Shipping,
    ItemSpecifics,
    ListingCondition,
)
from src.publisher import CrossPlatformPublisher

# Load environment variables
load_dotenv()


def create_sample_listings():
    """Create multiple sample listings"""

    listings = []

    # Listing 1: Sneakers
    listings.append(
        UnifiedListing(
            title="Nike Air Max 90 White/Black Size 11",
            description="Classic Air Max 90s in excellent condition. "
            "Minimal wear, clean uppers. Great everyday sneaker.",
            price=Price(amount=85.00),
            condition=ListingCondition.EXCELLENT,
            photos=[
                Photo(
                    url="https://example.com/airmax1.jpg",
                    order=0,
                    is_primary=True,
                )
            ],
            item_specifics=ItemSpecifics(
                brand="Nike",
                size="11",
                color="White/Black",
                model="Air Max 90",
            ),
            shipping=Shipping(cost=8.00),
            sku="NIKE-AM90-WB-11",
        )
    )

    # Listing 2: Watch
    listings.append(
        UnifiedListing(
            title="Casio G-Shock Digital Watch Black DW5600",
            description="Iconic G-Shock in black. Water resistant, shock resistant. "
            "Perfect condition, barely worn. Includes original box and manual.",
            price=Price(amount=60.00, compare_at_price=89.00),
            condition=ListingCondition.LIKE_NEW,
            photos=[
                Photo(
                    url="https://example.com/gshock1.jpg",
                    order=0,
                    is_primary=True,
                )
            ],
            item_specifics=ItemSpecifics(
                brand="Casio",
                model="DW5600",
                color="Black",
            ),
            shipping=Shipping(cost=5.00),
            sku="CASIO-GS-DW5600",
        )
    )

    # Listing 3: Headphones
    listings.append(
        UnifiedListing(
            title="Sony WH-1000XM4 Wireless Noise Cancelling Headphones Black",
            description="Premium Sony headphones with industry-leading noise cancellation. "
            "Excellent sound quality, 30-hour battery life. "
            "Gently used, all accessories included.",
            price=Price(amount=180.00, compare_at_price=349.00),
            condition=ListingCondition.EXCELLENT,
            photos=[
                Photo(
                    url="https://example.com/sony1.jpg",
                    order=0,
                    is_primary=True,
                )
            ],
            item_specifics=ItemSpecifics(
                brand="Sony",
                model="WH-1000XM4",
                color="Black",
            ),
            shipping=Shipping(cost=10.00),
            sku="SONY-WH1000XM4-BLK",
        )
    )

    return listings


def main():
    """Batch publish multiple listings"""

    print("📦 Batch Listing Example\n")

    # Create listings
    print("📝 Creating sample listings...")
    listings = create_sample_listings()
    print(f"   Created {len(listings)} listings\n")

    # Initialize publisher
    print("🔧 Initializing publisher...")
    publisher = CrossPlatformPublisher.from_env(auto_enhance=True)
    print()

    # Publish each listing
    all_results = []

    for i, listing in enumerate(listings, 1):
        print(f"📤 Publishing listing {i}/{len(listings)}: {listing.title}")

        # Publish to all platforms
        results = publisher.publish_to_all(listing)

        # Track results
        all_results.append({
            "listing": listing,
            "results": results,
        })

        # Show immediate feedback
        for platform, result in results.items():
            status = "✅" if result.success else "❌"
            print(f"   {status} {platform}")

        print()

        # Rate limiting - be nice to APIs
        if i < len(listings):
            print("   ⏳ Waiting 2 seconds before next listing...\n")
            time.sleep(2)

    # Summary
    print("=" * 60)
    print("📊 Batch Publishing Summary\n")

    total_listings = len(all_results)
    ebay_success = sum(
        1 for r in all_results
        if "eBay" in r["results"] and r["results"]["eBay"].success
    )
    mercari_success = sum(
        1 for r in all_results
        if "Mercari" in r["results"] and r["results"]["Mercari"].success
    )

    print(f"Total Listings: {total_listings}")
    print(f"eBay: {ebay_success}/{total_listings} successful")
    print(f"Mercari: {mercari_success}/{total_listings} successful")
    print()

    print(f"Overall Success Rate: {publisher.get_success_rate():.1f}%")

    # Show failures
    failures = []
    for item in all_results:
        for platform, result in item["results"].items():
            if not result.success:
                failures.append({
                    "title": item["listing"].title,
                    "platform": platform,
                    "error": result.error,
                })

    if failures:
        print("\n❌ Failed Listings:")
        for failure in failures:
            print(f"   - {failure['platform']}: {failure['title']}")
            print(f"     Error: {failure['error']}")


if __name__ == "__main__":
    main()
