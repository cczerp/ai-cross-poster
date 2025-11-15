"""
Mercari Adapter
===============
Converts UnifiedListing schema to Mercari format.

Supports both:
1. Mercari Shops API (official API for Mercari Shops sellers)
2. Automation layer (Puppeteer/Playwright for regular Mercari - headless browser)

Note: Regular Mercari does not have a public API, so automation is required.
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

    API documentation: https://developer.mercari.com/en (if available)
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
            Dictionary with listing_id
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
            - MERCARI_API_KEY
            - MERCARI_SHOP_ID
        """
        api_key = os.getenv("MERCARI_API_KEY")
        shop_id = os.getenv("MERCARI_SHOP_ID")

        if not all([api_key, shop_id]):
            raise ValueError(
                "Missing Mercari credentials in environment variables. "
                "Required: MERCARI_API_KEY, MERCARI_SHOP_ID"
            )

        return cls(api_key, shop_id, sandbox)


class MercariAutomationAdapter:
    """
    Adapter for regular Mercari using browser automation.

    Uses Playwright/Puppeteer to automate listing creation when API is not available.
    This is a fallback for regular Mercari sellers without Shops API access.
    """

    def __init__(
        self,
        email: str,
        password: str,
        headless: bool = True,
    ):
        """
        Initialize Mercari automation adapter.

        Args:
            email: Mercari account email
            password: Mercari account password
            headless: Run browser in headless mode
        """
        self.email = email
        self.password = password
        self.headless = headless
        self.browser = None
        self.page = None

    def _ensure_playwright(self):
        """Ensure Playwright is installed"""
        try:
            from playwright.sync_api import sync_playwright
            return sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for Mercari automation. "
                "Install with: pip install playwright && playwright install"
            )

    def _login(self):
        """Login to Mercari"""
        # This is a placeholder - actual implementation would navigate and login
        self.page.goto("https://www.mercari.com/login/")
        self.page.fill('input[name="email"]', self.email)
        self.page.fill('input[name="password"]', self.password)
        self.page.click('button[type="submit"]')
        self.page.wait_for_url("https://www.mercari.com/", timeout=10000)

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, str]:
        """
        Publish listing to Mercari using browser automation.

        Args:
            listing: UnifiedListing object

        Returns:
            Dictionary with listing_id and listing_url
        """
        sync_playwright = self._ensure_playwright()

        with sync_playwright() as p:
            # Launch browser
            self.browser = p.chromium.launch(headless=self.headless)
            self.page = self.browser.new_page()

            # Login
            self._login()

            # Navigate to sell page
            self.page.goto("https://www.mercari.com/sell/")

            # Fill in listing details
            title = listing.get_platform_title("mercari")
            self.page.fill('input[placeholder*="title"]', title)
            self.page.fill('textarea[placeholder*="description"]', listing.description)

            # Upload photos
            photos = listing.get_platform_photos("mercari")
            for photo in photos:
                if photo.local_path:
                    self.page.set_input_files('input[type="file"]', photo.local_path)

            # Set price
            self.page.fill('input[placeholder*="price"]', str(int(listing.price.amount)))

            # Select condition
            condition_text = self.CONDITION_MAP.get(
                listing.condition, "good"
            ).replace("_", " ").title()
            self.page.click(f'text="{condition_text}"')

            # Set category (if available)
            if listing.category:
                self.page.click(f'text="{listing.category.primary}"')

            # Submit listing
            self.page.click('button:has-text("List")')

            # Wait for success and get listing URL
            self.page.wait_for_url("**/item/**", timeout=15000)
            listing_url = self.page.url

            # Extract listing ID from URL
            listing_id = listing_url.split("/item/")[-1].split("/")[0]

            self.browser.close()

            return {
                "listing_id": listing_id,
                "listing_url": listing_url,
            }

    @classmethod
    def from_env(cls, headless: bool = True) -> "MercariAutomationAdapter":
        """
        Create adapter from environment variables.

        Expected variables:
            - MERCARI_EMAIL
            - MERCARI_PASSWORD
        """
        email = os.getenv("MERCARI_EMAIL")
        password = os.getenv("MERCARI_PASSWORD")

        if not all([email, password]):
            raise ValueError(
                "Missing Mercari credentials in environment variables. "
                "Required: MERCARI_EMAIL, MERCARI_PASSWORD"
            )

        return cls(email, password, headless)


class MercariAdapter:
    """
    Unified Mercari adapter that automatically chooses between Shops API and automation.
    """

    def __init__(self, use_shops_api: bool = True, **kwargs):
        """
        Initialize Mercari adapter.

        Args:
            use_shops_api: Use Shops API (True) or automation (False)
            **kwargs: Arguments for the specific adapter
        """
        if use_shops_api:
            self.adapter = MercariShopsAdapter(**kwargs)
        else:
            self.adapter = MercariAutomationAdapter(**kwargs)

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, str]:
        """Publish listing using the configured adapter"""
        return self.adapter.publish_listing(listing)

    @classmethod
    def from_env(cls) -> "MercariAdapter":
        """
        Create adapter from environment variables.

        Checks for MERCARI_API_KEY first (Shops API), falls back to automation.
        """
        api_key = os.getenv("MERCARI_API_KEY")

        if api_key:
            # Use Shops API
            return cls(
                use_shops_api=True,
                api_key=api_key,
                shop_id=os.getenv("MERCARI_SHOP_ID"),
            )
        else:
            # Use automation
            return cls(
                use_shops_api=False,
                email=os.getenv("MERCARI_EMAIL"),
                password=os.getenv("MERCARI_PASSWORD"),
            )
