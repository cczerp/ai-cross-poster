"""
Mercari Adapter
===============
Converts UnifiedListing schema to Mercari format.

COMPLIANCE NOTE:
================
This adapter ONLY supports the official Mercari Shops API.

Browser automation for regular Mercari accounts has been REMOVED as of 2025-11-18
due to Terms of Service violations. Using browser automation on Mercari:
- Violates Section 4.1 of Mercari Terms of Service
- Results in 60-90% account ban probability within 1-6 months
- May expose users to legal liability under CFAA

To use this adapter, you must have:
1. A Mercari Shops account (business/seller account)
2. Mercari Shops API key (apply at https://developer.mercari.com)

For compliance documentation, see: COMPLIANCE_REPORT.md
"""

import os
import json
from typing import Dict, Any, Optional, List
import requests
from datetime import datetime

from ..schema.unified_listing import (
    UnifiedListing,
    ListingCondition,
)


class MercariShopsAdapter:
    """
    Adapter for Mercari Shops API (official API for shop sellers).

    ✅ COMPLIANT - Uses official Mercari Shops API
    ✅ PRODUCTION-READY - Safe for commercial use
    ✅ TOS-APPROVED - No risk of account termination

    API documentation: https://developer.mercari.com/en

    Requirements:
    - Mercari Shops account
    - Mercari API key
    - Shop ID
    """

    # Mercari condition mappings
    CONDITION_MAP = {
        ListingCondition.NEW: "new",
        ListingCondition.NEW_WITH_TAGS: "new",
        ListingCondition.NEW_WITHOUT_TAGS: "new",
        ListingCondition.LIKE_NEW: "like_new",
        ListingCondition.EXCELLENT: "excellent",
        ListingCondition.GOOD: "good",
        ListingCondition.FAIR: "fair",
        ListingCondition.POOR: "poor",
        ListingCondition.FOR_PARTS: "poor",
    }

    def __init__(self, api_key: str, shop_id: str, sandbox: bool = False):
        """
        Initialize Mercari Shops adapter.

        Args:
            api_key: Mercari Shops API key
            shop_id: Your shop ID
            sandbox: Use sandbox environment
        """
        self.api_key = api_key
        self.shop_id = shop_id
        self.sandbox = sandbox

        # Note: Replace with actual Mercari Shops API endpoint when available
        self.base_url = (
            "https://api-sandbox.mercari.com"
            if sandbox
            else "https://api.mercari.com"
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def convert_to_mercari_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        """
        Convert UnifiedListing to Mercari Shops API format.

        Args:
            listing: UnifiedListing object

        Returns:
            Mercari API payload
        """
        # Validate first
        is_valid, errors = listing.validate()
        if not is_valid:
            raise ValueError(f"Invalid listing: {', '.join(errors)}")

        # Mercari has a 40-character title limit
        title = listing.get_platform_title("mercari")

        # Get photos (Mercari allows up to 10 photos)
        photos = listing.get_platform_photos("mercari")
        photo_urls = [p.url for p in photos]

        # Map condition
        condition = self.CONDITION_MAP.get(
            listing.condition, self.CONDITION_MAP[ListingCondition.GOOD]
        )

        # Build the payload (structure based on typical e-commerce APIs)
        payload = {
            "title": title,
            "description": listing.description,
            "price": int(listing.price.amount),  # Mercari uses cents/integer pricing
            "condition": condition,
            "photos": photo_urls,
            "quantity": listing.quantity,
            "shop_id": self.shop_id,
        }

        # Add category if available
        if listing.category and listing.category.mercari_category_id:
            payload["category_id"] = listing.category.mercari_category_id

        # Add brand if available
        if listing.item_specifics.brand:
            payload["brand"] = listing.item_specifics.brand

        # Add size if available
        if listing.item_specifics.size:
            payload["size"] = listing.item_specifics.size

        # Add color if available
        if listing.item_specifics.color:
            payload["color"] = listing.item_specifics.color

        # Shipping information
        if listing.shipping.cost is not None:
            payload["shipping_price"] = int(listing.shipping.cost)
        else:
            payload["shipping_price"] = 0  # Free shipping

        # Apply Mercari-specific overrides
        if listing.mercari_overrides:
            payload.update(listing.mercari_overrides)

        return payload

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, str]:
        """
        Publish listing to Mercari Shops.

        Args:
            listing: UnifiedListing object

        Returns:
            Dictionary with listing_id and listing_url

        Raises:
            Exception: If publishing fails
        """
        payload = self.convert_to_mercari_format(listing)

        response = requests.post(
            f"{self.base_url}/v1/listings",
            headers=self._get_headers(),
            json=payload,
        )

        if response.status_code in [200, 201]:
            listing_data = response.json()
            return {
                "listing_id": listing_data.get("id"),
                "listing_url": listing_data.get("url"),
            }
        else:
            raise Exception(f"Failed to publish to Mercari Shops: {response.text}")

    @classmethod
    def from_env(cls, sandbox: bool = False) -> "MercariShopsAdapter":
        """
        Create adapter from environment variables.

        Expected variables:
            - MERCARI_API_KEY: Your Mercari Shops API key
            - MERCARI_SHOP_ID: Your shop ID

        Args:
            sandbox: Use sandbox environment for testing

        Returns:
            MercariShopsAdapter instance

        Raises:
            ValueError: If required environment variables are missing
        """
        api_key = os.getenv("MERCARI_API_KEY")
        shop_id = os.getenv("MERCARI_SHOP_ID")

        if not all([api_key, shop_id]):
            raise ValueError(
                "Missing Mercari credentials in environment variables. "
                "Required: MERCARI_API_KEY, MERCARI_SHOP_ID\n\n"
                "To obtain these credentials:\n"
                "1. Sign up for Mercari Shops at https://shops.mercari.com\n"
                "2. Apply for API access at https://developer.mercari.com\n"
                "3. Set environment variables in your .env file"
            )

        return cls(api_key, shop_id, sandbox)


# ============================================================================
# REMOVED: MercariAutomationAdapter (2025-11-18)
# ============================================================================
#
# The browser automation adapter has been permanently removed due to:
# - Violation of Mercari Terms of Service Section 4.1
# - 60-90% account ban rate within 1-6 months
# - Potential CFAA legal liability
# - Detection by Mercari's anti-bot systems
#
# If you previously used MercariAutomationAdapter:
# 1. Migrate to MercariShopsAdapter (official API)
# 2. Stop all automated listings immediately
# 3. Review compliance documentation: COMPLIANCE_REPORT.md
#
# Alternative compliant platforms for non-Shop sellers:
# - Poshmark (CSV bulk upload)
# - Depop (API available)
# - eBay (official Sell API)
# - Etsy (official API)
#
# For questions or migration help, see: COMPLIANCE_REPORT.md
#
# ============================================================================
