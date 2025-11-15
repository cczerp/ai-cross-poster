"""
eBay Adapter
============
Converts UnifiedListing schema to eBay Sell API format.

API Documentation: https://developer.ebay.com/api-docs/sell/inventory/overview.html
"""

import os
import json
import base64
from typing import Dict, Any, Optional, List
import requests
from datetime import datetime, timedelta

from ..schema.unified_listing import (
    UnifiedListing,
    ListingCondition,
    ListingFormat,
    ShippingService,
)


class EbayAdapter:
    """
    Adapter for eBay Sell API (Trading API successor).
    Handles OAuth, inventory items, offers, and publishing.
    """

    # eBay condition ID mappings
    CONDITION_MAP = {
        ListingCondition.NEW: "1000",
        ListingCondition.NEW_WITH_TAGS: "1000",
        ListingCondition.NEW_WITHOUT_TAGS: "1500",
        ListingCondition.LIKE_NEW: "1500",
        ListingCondition.EXCELLENT: "2750",
        ListingCondition.GOOD: "3000",
        ListingCondition.FAIR: "4000",
        ListingCondition.POOR: "5000",
        ListingCondition.FOR_PARTS: "7000",
    }

    # eBay shipping service codes
    SHIPPING_SERVICE_MAP = {
        ShippingService.STANDARD: "USPSPriority",
        ShippingService.EXPEDITED: "FedEx2Day",
        ShippingService.OVERNIGHT: "FedExStandardOvernight",
        ShippingService.ECONOMY: "USPSMedia",
        ShippingService.FREE: "USPSPriority",
    }

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        sandbox: bool = False,
    ):
        """
        Initialize eBay adapter.

        Args:
            client_id: eBay application client ID
            client_secret: eBay application client secret
            refresh_token: OAuth refresh token (user consent token)
            sandbox: Use sandbox environment for testing
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.sandbox = sandbox

        self.base_url = (
            "https://api.sandbox.ebay.com"
            if sandbox
            else "https://api.ebay.com"
        )

        self.access_token = None
        self.token_expires_at = None

    def _ensure_access_token(self):
        """Ensure we have a valid access token, refresh if needed"""
        if (
            self.access_token
            and self.token_expires_at
            and datetime.now() < self.token_expires_at
        ):
            return

        # Get new access token using refresh token
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_b64 = base64.b64encode(auth_string.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_b64}",
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.marketing.readonly https://api.ebay.com/oauth/api_scope/sell.marketing https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account.readonly https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly https://api.ebay.com/oauth/api_scope/sell.fulfillment",
        }

        response = requests.post(
            f"{self.base_url}/identity/v1/oauth2/token",
            headers=headers,
            data=data,
        )

        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            expires_in = token_data["expires_in"]
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
        else:
            raise Exception(f"Failed to get access token: {response.text}")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with fresh access token"""
        self._ensure_access_token()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def convert_to_ebay_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        """
        Convert UnifiedListing to eBay Inventory Item format.

        Returns the payload for creating an inventory item.
        """
        # Validate first
        is_valid, errors = listing.validate()
        if not is_valid:
            raise ValueError(f"Invalid listing: {', '.join(errors)}")

        # Build product details
        product = {
            "title": listing.title,
            "description": listing.description,
            "aspects": {},  # Item specifics
            "imageUrls": [p.url for p in listing.get_platform_photos("ebay")],
        }

        # Add item specifics
        if listing.item_specifics:
            specs = listing.item_specifics.to_dict()
            # eBay expects aspects as {"aspect_name": ["value1", "value2"]}
            for key, value in specs.items():
                aspect_name = key.replace("_", " ").title()
                product["aspects"][aspect_name] = [str(value)]

        # Add brand if available (highly recommended for search)
        if listing.item_specifics.brand:
            product["brand"] = listing.item_specifics.brand

        # Add UPC/EAN/ISBN if available
        if listing.item_specifics.upc:
            product["upc"] = [listing.item_specifics.upc]
        if listing.item_specifics.isbn:
            product["isbn"] = [listing.item_specifics.isbn]

        # Build availability
        availability = {
            "shipToLocationAvailability": {
                "quantity": listing.quantity,
            }
        }

        # Build condition
        condition = self.CONDITION_MAP.get(
            listing.condition, self.CONDITION_MAP[ListingCondition.GOOD]
        )

        # Build the inventory item payload
        inventory_item = {
            "availability": availability,
            "condition": condition,
            "product": product,
        }

        # Apply any eBay-specific overrides
        if listing.ebay_overrides:
            inventory_item.update(listing.ebay_overrides)

        return inventory_item

    def create_offer_payload(self, listing: UnifiedListing, sku: str) -> Dict[str, Any]:
        """
        Create an offer payload for publishing the listing.

        Args:
            listing: UnifiedListing object
            sku: SKU of the inventory item

        Returns:
            Offer payload for eBay API
        """
        # Determine listing format
        format_type = (
            "AUCTION"
            if listing.listing_format == ListingFormat.AUCTION
            else "FIXED_PRICE"
        )

        # Build pricing
        pricing = {
            "price": {
                "value": str(listing.price.amount),
                "currency": listing.price.currency,
            }
        }

        # Add quantity
        quantity = listing.quantity

        # Build listing policies (simplified - you'd typically reference policy IDs)
        listing_policies = {
            "fulfillmentPolicyId": None,  # Must be set via eBay account
            "paymentPolicyId": None,  # Must be set via eBay account
            "returnPolicyId": None,  # Must be set via eBay account
        }

        # Build shipping cost override if specified
        shipping_cost_overrides = []
        if listing.shipping.cost is not None:
            shipping_service = self.SHIPPING_SERVICE_MAP.get(
                listing.shipping.service, "USPSPriority"
            )
            shipping_cost_overrides.append({
                "shippingServiceType": "DOMESTIC",
                "shippingCost": {
                    "value": str(listing.shipping.cost),
                    "currency": listing.price.currency,
                },
            })

        # Category ID (must be provided - would typically come from category mapping)
        category_id = None
        if listing.category and listing.category.ebay_category_id:
            category_id = listing.category.ebay_category_id

        # Build offer
        offer = {
            "sku": sku,
            "marketplaceId": "EBAY_US",
            "format": format_type,
            "listingDescription": listing.description,
            "listingPolicies": listing_policies,
            "pricingSummary": pricing,
            "quantityLimitPerBuyer": 10,  # Reasonable default
            "availableQuantity": quantity,
        }

        if category_id:
            offer["categoryId"] = category_id

        if listing.duration_days:
            # Only for auctions
            if format_type == "AUCTION":
                offer["listingDuration"] = f"DAYS_{listing.duration_days}"

        return offer

    def create_inventory_item(self, listing: UnifiedListing, sku: Optional[str] = None) -> str:
        """
        Create an inventory item on eBay.

        Args:
            listing: UnifiedListing object
            sku: Optional SKU (will generate if not provided)

        Returns:
            SKU of the created inventory item
        """
        if sku is None:
            # Generate SKU
            sku = listing.sku or f"auto_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        payload = self.convert_to_ebay_format(listing)

        response = requests.put(
            f"{self.base_url}/sell/inventory/v1/inventory_item/{sku}",
            headers=self._get_headers(),
            json=payload,
        )

        if response.status_code in [200, 201, 204]:
            return sku
        else:
            raise Exception(f"Failed to create inventory item: {response.text}")

    def create_offer(self, listing: UnifiedListing, sku: str) -> str:
        """
        Create an offer (publish the listing).

        Args:
            listing: UnifiedListing object
            sku: SKU of the inventory item

        Returns:
            Offer ID
        """
        payload = self.create_offer_payload(listing, sku)

        response = requests.post(
            f"{self.base_url}/sell/inventory/v1/offer",
            headers=self._get_headers(),
            json=payload,
        )

        if response.status_code in [200, 201]:
            offer_data = response.json()
            return offer_data.get("offerId")
        else:
            raise Exception(f"Failed to create offer: {response.text}")

    def publish_offer(self, offer_id: str) -> str:
        """
        Publish an offer to eBay.

        Args:
            offer_id: The offer ID to publish

        Returns:
            Listing ID
        """
        response = requests.post(
            f"{self.base_url}/sell/inventory/v1/offer/{offer_id}/publish",
            headers=self._get_headers(),
        )

        if response.status_code == 200:
            publish_data = response.json()
            return publish_data.get("listingId")
        else:
            raise Exception(f"Failed to publish offer: {response.text}")

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, str]:
        """
        Complete workflow: create inventory item, create offer, and publish.

        Args:
            listing: UnifiedListing object

        Returns:
            Dictionary with sku, offer_id, and listing_id
        """
        # Step 1: Create inventory item
        sku = self.create_inventory_item(listing)

        # Step 2: Create offer
        offer_id = self.create_offer(listing, sku)

        # Step 3: Publish offer
        listing_id = self.publish_offer(offer_id)

        return {
            "sku": sku,
            "offer_id": offer_id,
            "listing_id": listing_id,
        }

    @classmethod
    def from_env(cls, sandbox: bool = False) -> "EbayAdapter":
        """
        Create adapter from environment variables.

        Expected variables:
            - EBAY_CLIENT_ID
            - EBAY_CLIENT_SECRET
            - EBAY_REFRESH_TOKEN
        """
        client_id = os.getenv("EBAY_CLIENT_ID")
        client_secret = os.getenv("EBAY_CLIENT_SECRET")
        refresh_token = os.getenv("EBAY_REFRESH_TOKEN")

        if not all([client_id, client_secret, refresh_token]):
            raise ValueError(
                "Missing eBay credentials in environment variables. "
                "Required: EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REFRESH_TOKEN"
            )

        return cls(client_id, client_secret, refresh_token, sandbox)
