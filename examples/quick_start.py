"""
Quick Start Example
===================
Simplest way to create and publish a listing to all platforms.
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
from src.publisher import publish_to_all

# Load environment variables
load_dotenv()


def main():
    """Create and publish a simple listing"""

    # Create a basic listing
    listing = UnifiedListing(
        title="Vintage Nike Air Jordan 1 High Top Sneakers Size 10",
        description="Classic Air Jordan 1s in great condition. "
        "Minimal wear, original box included. "
        "Perfect for collectors or everyday wear.",
        price=Price(amount=150.00, compare_at_price=200.00),
        condition=ListingCondition.EXCELLENT,
        photos=[
            Photo(
                url="https://example.com/photo1.jpg",
                local_path="/path/to/photo1.jpg",
                order=0,
                is_primary=True,
            ),
            Photo(
                url="https://example.com/photo2.jpg",
                local_path="/path/to/photo2.jpg",
                order=1,
            ),
        ],
        shipping=Shipping(
            cost=10.00,
            handling_time_days=2,
        ),
        quantity=1,
    )

    # Publish to all platforms (with AI enhancement enabled by default)
    print("📤 Publishing listing to all platforms...")
    results = publish_to_all(listing)

    # Check results
    for platform, result in results.items():
        if result.success:
            print(f"✅ {platform}: Published successfully!")
            print(f"   Listing ID: {result.listing_id}")
            if result.listing_url:
                print(f"   URL: {result.listing_url}")
        else:
            print(f"❌ {platform}: Failed to publish")
            print(f"   Error: {result.error}")


if __name__ == "__main__":
    main()
