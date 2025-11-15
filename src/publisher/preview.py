"""
Preview and Confirmation Module
================================
Allows users to preview how listings will appear on each platform
before actual posting, and confirm fields are properly filled.
"""

from typing import Dict, Any
from ..schema.unified_listing import UnifiedListing


class ListingPreviewer:
    """
    Preview how a listing will appear on each platform before publishing.
    """

    def preview_for_ebay(self, listing: UnifiedListing) -> Dict[str, Any]:
        """
        Show how the listing will appear on eBay.

        Returns:
            Dictionary with formatted preview data
        """
        from ..adapters.ebay_adapter import EbayAdapter

        # Create a temporary adapter instance for format conversion
        preview = {
            "platform": "eBay",
            "title": listing.title,
            "title_length": f"{len(listing.title)}/80 characters",
            "description": listing.description,
            "price": f"${listing.price.amount:.2f}",
            "condition": listing.condition.value.replace("_", " ").title(),
            "photos": len(listing.photos),
            "photo_limit": "12 max",
            "shipping_cost": f"${listing.shipping.cost:.2f}" if listing.shipping.cost else "Free",
            "item_specifics": listing.item_specifics.to_dict() if listing.item_specifics else {},
            "keywords": listing.seo_data.keywords if listing.seo_data else [],
        }

        # Check for any issues
        issues = []
        if len(listing.title) > 80:
            issues.append("⚠️  Title exceeds eBay's 80 character limit")
        if len(listing.photos) > 12:
            issues.append("⚠️  Too many photos (eBay max: 12)")
        if not listing.item_specifics.brand:
            issues.append("💡 Tip: Adding brand improves search visibility")

        preview["issues"] = issues
        return preview

    def preview_for_mercari(self, listing: UnifiedListing) -> Dict[str, Any]:
        """
        Show how the listing will appear on Mercari.

        Returns:
            Dictionary with formatted preview data
        """
        mercari_title = listing.get_platform_title("mercari")
        mercari_photos = listing.get_platform_photos("mercari")

        preview = {
            "platform": "Mercari",
            "title": mercari_title,
            "title_length": f"{len(mercari_title)}/40 characters",
            "description": listing.description,
            "price": f"${listing.price.amount:.2f}",
            "condition": listing.condition.value.replace("_", " ").title(),
            "photos": len(mercari_photos),
            "photo_limit": "10 max",
            "shipping_cost": f"${listing.shipping.cost:.2f}" if listing.shipping.cost else "Free",
            "brand": listing.item_specifics.brand if listing.item_specifics else "N/A",
        }

        # Check for any issues
        issues = []
        if len(listing.title) > 40:
            issues.append(f"⚠️  Title truncated to {len(mercari_title)} characters for Mercari")
        if len(listing.photos) > 10:
            issues.append(f"⚠️  Photos limited to 10 for Mercari (you have {len(listing.photos)})")
        if not listing.item_specifics.brand:
            issues.append("💡 Tip: Brand is important for Mercari search")

        preview["issues"] = issues
        return preview

    def preview_all(self, listing: UnifiedListing) -> Dict[str, Dict[str, Any]]:
        """
        Preview for all platforms.

        Returns:
            Dictionary with preview data for each platform
        """
        return {
            "eBay": self.preview_for_ebay(listing),
            "Mercari": self.preview_for_mercari(listing),
        }

    def print_preview(self, listing: UnifiedListing):
        """
        Print a formatted preview to console for user review.
        """
        previews = self.preview_all(listing)

        print("\n" + "="*70)
        print("📋 LISTING PREVIEW")
        print("="*70)

        for platform, data in previews.items():
            print(f"\n🔷 {platform}")
            print("-"*70)
            print(f"Title: {data['title']}")
            print(f"       ({data['title_length']})")
            print(f"\nPrice: {data['price']}")
            print(f"Condition: {data['condition']}")
            print(f"Photos: {data['photos']} ({data['photo_limit']})")
            print(f"Shipping: {data['shipping_cost']}")

            if data.get('item_specifics'):
                print(f"\nItem Specifics:")
                for key, value in data['item_specifics'].items():
                    print(f"  • {key}: {value}")

            if data.get('keywords'):
                print(f"\nKeywords: {', '.join(data['keywords'][:5])}...")

            print(f"\nDescription:")
            desc_preview = data['description'][:200]
            print(f"  {desc_preview}..." if len(data['description']) > 200 else f"  {desc_preview}")

            # Show any issues
            if data.get('issues'):
                print(f"\n⚠️  Issues/Tips:")
                for issue in data['issues']:
                    print(f"  {issue}")

        print("\n" + "="*70)


def confirm_publish(listing: UnifiedListing, platforms: list = None) -> bool:
    """
    Show preview and ask user to confirm before publishing.

    Args:
        listing: The listing to preview
        platforms: List of platforms to publish to

    Returns:
        True if user confirms, False otherwise
    """
    previewer = ListingPreviewer()
    previewer.print_preview(listing)

    # Validate before asking
    is_valid, errors = listing.validate()
    if not is_valid:
        print("\n❌ VALIDATION ERRORS:")
        for error in errors:
            print(f"  • {error}")
        return False

    # Ask for confirmation
    platform_list = ", ".join(platforms) if platforms else "all platforms"
    response = input(f"\n✅ Ready to publish to {platform_list}? (yes/no): ")

    return response.lower() in ['yes', 'y']
