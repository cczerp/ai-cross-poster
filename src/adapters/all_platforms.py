"""
All Platform Adapters
======================
Comprehensive adapters for all 17 supported platforms.

✅ 100% TOS-COMPLIANT
✅ No browser automation
✅ Only official APIs, CSV uploads, or manual templates

Platforms:
- API: Etsy, Shopify, WooCommerce, Depop, Square, Pinterest
- CSV: Poshmark, Bonanza, Ecrater, Ruby Lane, OfferUp
- Feed: Facebook Shops, Google Shopping
- Template: Craigslist, VarageSale, Nextdoor, Chairish
"""

import os
import csv
import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from .base_adapter import (
    APIAdapter, CSVAdapter, FeedAdapter, TemplateAdapter,
    IntegrationType, ComplianceStatus
)
from .platform_configs import get_platform_mapper
from ..schema.unified_listing import UnifiedListing


# ============================================================================
# API ADAPTERS (Direct posting)
# ============================================================================

class EtsyAdapter(APIAdapter):
    """Etsy API v3 adapter"""

    def __init__(self, api_key: str, shop_id: str):
        super().__init__()
        self.api_key = api_key
        self.shop_id = shop_id
        self.base_url = "https://openapi.etsy.com/v3"
        self.mapper = get_platform_mapper("etsy")

    def get_platform_name(self) -> str:
        return "Etsy"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        try:
            response = requests.get(
                f"{self.base_url}/application/shops/{self.shop_id}",
                headers=self._get_headers()
            )
            return (response.status_code == 200, None)
        except Exception as e:
            return (False, str(e))

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

    def _get_api_endpoint(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint}"

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        data = self.mapper.map_listing(listing)
        data["who_made"] = data.get("who_made", "someone_else")
        data["when_made"] = data.get("when_made", "2020_2024")
        data["is_supply"] = False
        return data

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        payload = self.convert_to_platform_format(listing)

        response = requests.post(
            self._get_api_endpoint(f"application/shops/{self.shop_id}/listings"),
            headers=self._get_headers(),
            json=payload
        )

        if response.status_code in [200, 201]:
            data = response.json()
            return {
                "success": True,
                "listing_id": str(data.get("listing_id")),
                "listing_url": data.get("url"),
            }
        else:
            return {
                "success": False,
                "error": response.text,
            }


class ShopifyAdapter(APIAdapter):
    """Shopify Admin API adapter"""

    def __init__(self, shop_url: str, access_token: str):
        super().__init__()
        self.shop_url = shop_url.rstrip('/')
        self.access_token = access_token
        self.mapper = get_platform_mapper("shopify")

    def get_platform_name(self) -> str:
        return "Shopify"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        try:
            response = requests.get(
                f"{self.shop_url}/admin/api/2024-01/shop.json",
                headers=self._get_headers()
            )
            return (response.status_code == 200, None)
        except Exception as e:
            return (False, str(e))

    def _get_headers(self) -> Dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    def _get_api_endpoint(self, endpoint: str) -> str:
        return f"{self.shop_url}/admin/api/2024-01/{endpoint}"

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        data = self.mapper.map_listing(listing)

        # Shopify requires specific structure
        product = {
            "product": {
                "title": data["title"],
                "body_html": data["body_html"],
                "vendor": data.get("vendor", ""),
                "product_type": data.get("product_type", ""),
                "tags": ", ".join(data.get("tags", [])),
                "variants": [{
                    "price": str(data["price"]),
                    "sku": data.get("sku", ""),
                    "inventory_quantity": data.get("inventory_quantity", 1),
                }]
            }
        }

        return product

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        payload = self.convert_to_platform_format(listing)

        response = requests.post(
            self._get_api_endpoint("products.json"),
            headers=self._get_headers(),
            json=payload
        )

        if response.status_code in [200, 201]:
            data = response.json()
            product = data.get("product", {})
            return {
                "success": True,
                "listing_id": str(product.get("id")),
                "listing_url": f"{self.shop_url}/products/{product.get('handle')}",
            }
        else:
            return {
                "success": False,
                "error": response.text,
            }


class WooCommerceAdapter(APIAdapter):
    """WooCommerce REST API adapter"""

    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        super().__init__()
        self.site_url = site_url.rstrip('/')
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.mapper = get_platform_mapper("woocommerce")

    def get_platform_name(self) -> str:
        return "WooCommerce"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        try:
            response = requests.get(
                f"{self.site_url}/wp-json/wc/v3/system_status",
                auth=(self.consumer_key, self.consumer_secret)
            )
            return (response.status_code == 200, None)
        except Exception as e:
            return (False, str(e))

    def _get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    def _get_api_endpoint(self, endpoint: str) -> str:
        return f"{self.site_url}/wp-json/wc/v3/{endpoint}"

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return self.mapper.map_listing(listing)

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        payload = self.convert_to_platform_format(listing)

        response = requests.post(
            self._get_api_endpoint("products"),
            auth=(self.consumer_key, self.consumer_secret),
            json=payload
        )

        if response.status_code in [200, 201]:
            data = response.json()
            return {
                "success": True,
                "listing_id": str(data.get("id")),
                "listing_url": data.get("permalink"),
            }
        else:
            return {
                "success": False,
                "error": response.text,
            }


class DepopAdapter(APIAdapter):
    """Depop API adapter (for approved sellers)"""

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.base_url = "https://api.depop.com/v1"
        self.mapper = get_platform_mapper("depop")

    def get_platform_name(self) -> str:
        return "Depop"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        return (True, None)  # Simplified

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _get_api_endpoint(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint}"

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return self.mapper.map_listing(listing)

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        # Note: Actual Depop API endpoints may differ
        # Contact Depop for official API documentation
        return {
            "success": False,
            "error": "Depop API integration requires approval. Contact business@depop.com"
        }


class SquareAdapter(APIAdapter):
    """Square Catalog API adapter"""

    def __init__(self, access_token: str, location_id: str):
        super().__init__()
        self.access_token = access_token
        self.location_id = location_id
        self.base_url = "https://connect.squareup.com/v2"
        self.mapper = get_platform_mapper("square")

    def get_platform_name(self) -> str:
        return "Square"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        try:
            response = requests.get(
                f"{self.base_url}/locations",
                headers=self._get_headers()
            )
            return (response.status_code == 200, None)
        except Exception as e:
            return (False, str(e))

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Square-Version": "2024-01-18",
        }

    def _get_api_endpoint(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint}"

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        data = self.mapper.map_listing(listing)

        # Square requires specific catalog object structure
        catalog_object = {
            "type": "ITEM",
            "id": f"#{listing.sku or 'auto'}",
            "item_data": {
                "name": data["name"],
                "description": data.get("description", ""),
                "variations": [{
                    "type": "ITEM_VARIATION",
                    "id": "#variation-1",
                    "item_variation_data": {
                        "item_id": f"#{listing.sku or 'auto'}",
                        "name": "Regular",
                        "pricing_type": "FIXED_PRICING",
                        "price_money": {
                            "amount": data["price_money"],
                            "currency": "USD"
                        },
                        "track_inventory": data.get("track_inventory", True),
                    }
                }]
            }
        }

        return {"object": catalog_object}

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        payload = self.convert_to_platform_format(listing)

        response = requests.post(
            self._get_api_endpoint("catalog/object"),
            headers=self._get_headers(),
            json=payload
        )

        if response.status_code in [200, 201]:
            data = response.json()
            return {
                "success": True,
                "listing_id": data.get("catalog_object", {}).get("id"),
            }
        else:
            return {
                "success": False,
                "error": response.text,
            }


class PinterestAdapter(APIAdapter):
    """Pinterest Pins API adapter"""

    def __init__(self, access_token: str):
        super().__init__()
        self.access_token = access_token
        self.base_url = "https://api.pinterest.com/v5"
        self.mapper = get_platform_mapper("pinterest")

    def get_platform_name(self) -> str:
        return "Pinterest"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        try:
            response = requests.get(
                f"{self.base_url}/user_account",
                headers=self._get_headers()
            )
            return (response.status_code == 200, None)
        except Exception as e:
            return (False, str(e))

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _get_api_endpoint(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint}"

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return self.mapper.map_listing(listing)

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        payload = self.convert_to_platform_format(listing)

        response = requests.post(
            self._get_api_endpoint("pins"),
            headers=self._get_headers(),
            json=payload
        )

        if response.status_code in [200, 201]:
            data = response.json()
            return {
                "success": True,
                "listing_id": data.get("id"),
                "listing_url": data.get("link"),
            }
        else:
            return {
                "success": False,
                "error": response.text,
            }


# ============================================================================
# CSV ADAPTERS (Bulk upload files)
# ============================================================================

class BonanzaAdapter(CSVAdapter):
    """Bonanza CSV import adapter"""

    def __init__(self, output_dir: str = "./data/csv_exports"):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mapper = get_platform_mapper("bonanza")

    def get_platform_name(self) -> str:
        return "Bonanza"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_csv_headers(self) -> List[str]:
        return ["Title", "Description", "Price", "Quantity", "Category"]

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return self.mapper.map_listing(listing)

    def generate_csv(self, listings: List[UnifiedListing]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"bonanza_{timestamp}.csv"

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.get_csv_headers())
            writer.writeheader()
            for listing in listings:
                row = self.convert_to_platform_format(listing)
                writer.writerow(row)

        return str(filepath)

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        csv_path = self.generate_csv([listing])
        return {
            "success": True,
            "file_path": csv_path,
            "message": "CSV generated. Upload to Bonanza: https://www.bonanza.com/booth/manage_items/bulk_import",
            "requires_manual_action": True,
        }


class EcraterAdapter(CSVAdapter):
    """Ecrater CSV import adapter"""

    def __init__(self, output_dir: str = "./data/csv_exports"):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mapper = get_platform_mapper("ecrater")

    def get_platform_name(self) -> str:
        return "Ecrater"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_csv_headers(self) -> List[str]:
        return ["title", "description", "price", "quantity"]

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return self.mapper.map_listing(listing)

    def generate_csv(self, listings: List[UnifiedListing]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"ecrater_{timestamp}.csv"

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.get_csv_headers())
            writer.writeheader()
            for listing in listings:
                row = self.convert_to_platform_format(listing)
                writer.writerow(row)

        return str(filepath)

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        csv_path = self.generate_csv([listing])
        return {
            "success": True,
            "file_path": csv_path,
            "message": "CSV generated. Upload to Ecrater bulk import tool",
            "requires_manual_action": True,
        }


class RubyLaneAdapter(CSVAdapter):
    """Ruby Lane CSV import adapter"""

    def __init__(self, output_dir: str = "./data/csv_exports"):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mapper = get_platform_mapper("ruby lane")

    def get_platform_name(self) -> str:
        return "Ruby Lane"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_csv_headers(self) -> List[str]:
        return ["Item Title", "Description", "Price"]

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return self.mapper.map_listing(listing)

    def generate_csv(self, listings: List[UnifiedListing]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"rubylane_{timestamp}.csv"

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.get_csv_headers())
            writer.writeheader()
            for listing in listings:
                row = self.convert_to_platform_format(listing)
                writer.writerow(row)

        return str(filepath)

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        csv_path = self.generate_csv([listing])
        return {
            "success": True,
            "file_path": csv_path,
            "message": "CSV generated. Upload to Ruby Lane seller tools",
            "requires_manual_action": True,
        }


class OfferUpAdapter(CSVAdapter):
    """OfferUp CSV export adapter"""

    def __init__(self, output_dir: str = "./data/csv_exports"):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mapper = get_platform_mapper("offerup")

    def get_platform_name(self) -> str:
        return "OfferUp"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def get_csv_headers(self) -> List[str]:
        return ["title", "description", "price", "category"]

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return self.mapper.map_listing(listing)

    def generate_csv(self, listings: List[UnifiedListing]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"offerup_{timestamp}.csv"

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.get_csv_headers())
            writer.writeheader()
            for listing in listings:
                row = self.convert_to_platform_format(listing)
                writer.writerow(row)

        return str(filepath)

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        csv_path = self.generate_csv([listing])
        return {
            "success": True,
            "file_path": csv_path,
            "message": "CSV generated for reference. OfferUp requires manual posting via mobile app",
            "requires_manual_action": True,
        }


# ============================================================================
# FEED ADAPTERS (Product catalogs/feeds)
# ============================================================================

class FacebookShopsAdapter(FeedAdapter):
    """Facebook Shops product catalog adapter"""

    def __init__(self, catalog_id: str, access_token: str, output_dir: str = "./data/feeds"):
        super().__init__()
        self.catalog_id = catalog_id
        self.access_token = access_token
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mapper = get_platform_mapper("facebook")
        self.base_url = "https://graph.facebook.com/v18.0"

    def get_platform_name(self) -> str:
        return "Facebook Shops"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        try:
            response = requests.get(
                f"{self.base_url}/{self.catalog_id}",
                params={"access_token": self.access_token}
            )
            return (response.status_code == 200, None)
        except Exception as e:
            return (False, str(e))

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return self.mapper.map_listing(listing)

    def generate_feed(self, listings: List[UnifiedListing], format: str = "csv") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"facebook_catalog_{timestamp}.csv"

        headers = [
            "id", "title", "description", "availability", "condition",
            "price", "link", "image_link", "brand", "google_product_category"
        ]

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for listing in listings:
                row = self.convert_to_platform_format(listing)
                writer.writerow(row)

        return str(filepath)

    def upload_feed(self, feed_path: str) -> Dict[str, Any]:
        """Upload feed to Facebook Catalog"""
        # Note: This would use Facebook's Catalog API
        # For now, user uploads manually
        return {
            "success": True,
            "message": f"Feed generated: {feed_path}. Upload to Facebook Commerce Manager",
            "requires_manual_action": True,
        }

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        feed_path = self.generate_feed([listing])
        return {
            "success": True,
            "file_path": feed_path,
            "message": "Feed generated. Upload to Facebook Commerce Manager",
            "requires_manual_action": True,
        }


class GoogleShoppingAdapter(FeedAdapter):
    """Google Shopping / Merchant Center adapter"""

    def __init__(self, merchant_id: str, output_dir: str = "./data/feeds"):
        super().__init__()
        self.merchant_id = merchant_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mapper = get_platform_mapper("google shopping")

    def get_platform_name(self) -> str:
        return "Google Shopping"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        return (True, None)  # Simplified

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return self.mapper.map_listing(listing)

    def generate_feed(self, listings: List[UnifiedListing], format: str = "csv") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"google_shopping_{timestamp}.csv"

        headers = [
            "id", "title", "description", "link", "image_link",
            "availability", "price", "condition", "brand", "gtin", "mpn",
            "google_product_category"
        ]

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for listing in listings:
                row = self.convert_to_platform_format(listing)
                writer.writerow(row)

        return str(filepath)

    def upload_feed(self, feed_path: str) -> Dict[str, Any]:
        return {
            "success": True,
            "message": f"Feed generated: {feed_path}. Upload to Google Merchant Center",
            "requires_manual_action": True,
        }

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        feed_path = self.generate_feed([listing])
        return {
            "success": True,
            "file_path": feed_path,
            "message": "Feed generated. Upload to Google Merchant Center",
            "requires_manual_action": True,
        }


# ============================================================================
# TEMPLATE ADAPTERS (Manual posting assistance)
# ============================================================================

class CraigslistAdapter(TemplateAdapter):
    """Craigslist email template adapter (NO AUTOMATION - TOS COMPLIANT)"""

    def get_platform_name(self) -> str:
        return "Craigslist"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return {
            "title": listing.title[:70],  # Craigslist limit
            "description": listing.description,
            "price": f"${listing.price.amount:.2f}",
        }

    def generate_template(self, listing: UnifiedListing) -> Dict[str, str]:
        data = self.convert_to_platform_format(listing)

        formatted_text = f"""
CRAIGSLIST POSTING TEMPLATE
===========================

Title: {data['title']}

Price: {data['price']}

Description:
{data['description']}

---
Photos to upload:
"""
        for i, photo in enumerate(listing.photos[:24], 1):  # Craigslist allows 24
            formatted_text += f"{i}. {photo.url or photo.local_path}\n"

        formatted_text += """
---
INSTRUCTIONS:
1. Go to https://craigslist.org
2. Click "post to classifieds"
3. Select your category
4. Copy the title and description above
5. Enter price
6. Upload photos
7. Review and publish
"""

        return {
            "title": data["title"],
            "description": data["description"],
            "formatted_text": formatted_text,
        }


class VarageSaleAdapter(TemplateAdapter):
    """VarageSale template adapter (NO AUTOMATION - TOS COMPLIANT)"""

    def get_platform_name(self) -> str:
        return "VarageSale"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return {
            "title": listing.title[:80],
            "description": listing.description[:1000],  # VarageSale limit
            "price": f"${listing.price.amount:.2f}",
        }

    def generate_template(self, listing: UnifiedListing) -> Dict[str, str]:
        data = self.convert_to_platform_format(listing)

        formatted_text = f"""
VARAGESALE POSTING TEMPLATE
============================

Title: {data['title']}

Price: {data['price']}

Description:
{data['description']}

---
Photos to upload: {len(listing.photos)} photos ready

---
INSTRUCTIONS:
1. Open VarageSale mobile app
2. Tap "Sell Something"
3. Select category
4. Copy title and description above
5. Enter price
6. Upload photos from your device
7. Select your neighborhood
8. Post listing
"""

        return {
            "title": data["title"],
            "description": data["description"],
            "formatted_text": formatted_text,
        }


class NextdoorAdapter(TemplateAdapter):
    """Nextdoor Business template adapter"""

    def get_platform_name(self) -> str:
        return "Nextdoor Business"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return {
            "title": listing.title[:80],
            "description": listing.description[:1500],
            "price": f"${listing.price.amount:.2f}",
        }

    def generate_template(self, listing: UnifiedListing) -> Dict[str, str]:
        data = self.convert_to_platform_format(listing)

        formatted_text = f"""
NEXTDOOR BUSINESS POSTING TEMPLATE
===================================

Title: {data['title']}

Price: {data['price']}

Description:
{data['description']}

---
Photos to upload: {len(listing.photos)} photos ready

---
INSTRUCTIONS:
1. Go to https://business.nextdoor.com
2. Create a business post
3. Copy title and description above
4. Add price
5. Upload photos
6. Select your service area
7. Publish post
"""

        return {
            "title": data["title"],
            "description": data["description"],
            "formatted_text": formatted_text,
        }


class ChairishAdapter(TemplateAdapter):
    """Chairish template adapter (NO AUTOMATION - TOS COMPLIANT)"""

    def get_platform_name(self) -> str:
        return "Chairish"

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        return (True, None)

    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        return {
            "title": listing.title,
            "description": listing.description,
            "price": f"${listing.price.amount:.2f}",
            "brand": listing.item_specifics.brand or "",
        }

    def generate_template(self, listing: UnifiedListing) -> Dict[str, str]:
        data = self.convert_to_platform_format(listing)

        formatted_text = f"""
CHAIRISH POSTING TEMPLATE
=========================

Title: {data['title']}

Price: {data['price']}

Brand/Designer: {data['brand']}

Description:
{data['description']}

---
Photos to upload: {len(listing.photos)} photos ready

---
INSTRUCTIONS:
1. Go to https://www.chairish.com/shop/create-listing
2. Select "Furniture" or appropriate category
3. Enter title and description above
4. Add brand/designer
5. Enter price
6. Upload photos (professional photos recommended)
7. Add dimensions if applicable
8. Review and submit for approval
"""

        return {
            "title": data["title"],
            "description": data["description"],
            "formatted_text": formatted_text,
        }


# ============================================================================
# PLATFORM REGISTRY
# ============================================================================

PLATFORM_ADAPTERS = {
    # API Platforms
    "etsy": EtsyAdapter,
    "shopify": ShopifyAdapter,
    "woocommerce": WooCommerceAdapter,
    "depop": DepopAdapter,
    "square": SquareAdapter,
    "pinterest": PinterestAdapter,

    # CSV Platforms
    "poshmark": None,  # Use poshmark_adapter.py
    "bonanza": BonanzaAdapter,
    "ecrater": EcraterAdapter,
    "rubylane": RubyLaneAdapter,
    "ruby lane": RubyLaneAdapter,
    "offerup": OfferUpAdapter,

    # Feed Platforms
    "facebook": FacebookShopsAdapter,
    "facebook shops": FacebookShopsAdapter,
    "google shopping": GoogleShoppingAdapter,
    "google": GoogleShoppingAdapter,

    # Template Platforms
    "craigslist": CraigslistAdapter,
    "varagesale": VarageSaleAdapter,
    "nextdoor": NextdoorAdapter,
    "chairish": ChairishAdapter,
}


def get_adapter_class(platform_name: str):
    """
    Get adapter class for a platform.

    Args:
        platform_name: Platform name (case-insensitive)

    Returns:
        Adapter class

    Raises:
        ValueError: If platform not found
    """
    platform_lower = platform_name.lower()
    adapter_class = PLATFORM_ADAPTERS.get(platform_lower)

    if adapter_class is None:
        if platform_lower == "poshmark":
            raise ValueError("Use PoshmarkAdapter from poshmark_adapter.py")
        raise ValueError(
            f"Platform '{platform_name}' not found. "
            f"Available: {', '.join(PLATFORM_ADAPTERS.keys())}"
        )

    return adapter_class

