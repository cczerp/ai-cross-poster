"""
AI Cross-Poster
===============
Analyzes images to create optimized listings on multiple resell platforms.

Main components:
- schema: Unified listing schema
- adapters: Platform-specific adapters (eBay, Mercari)
- enhancer: AI-powered listing enhancement
- publisher: Cross-platform publishing orchestrator
"""

from .schema import (
    UnifiedListing,
    Photo,
    Price,
    Shipping,
    Category,
    ItemSpecifics,
    SEOData,
    ListingCondition,
    ListingFormat,
)

from .adapters import (
    EbayAdapter,
    MercariAdapter,
)

from .enhancer import (
    AIEnhancer,
    enhance_listing,
)

from .publisher import (
    CrossPlatformPublisher,
    PublishResult,
    publish_to_ebay,
    publish_to_mercari,
    publish_to_all,
)

__version__ = "1.0.0"

__all__ = [
    # Schema
    "UnifiedListing",
    "Photo",
    "Price",
    "Shipping",
    "Category",
    "ItemSpecifics",
    "SEOData",
    "ListingCondition",
    "ListingFormat",
    # Adapters
    "EbayAdapter",
    "MercariAdapter",
    # Enhancer
    "AIEnhancer",
    "enhance_listing",
    # Publisher
    "CrossPlatformPublisher",
    "PublishResult",
    "publish_to_ebay",
    "publish_to_mercari",
    "publish_to_all",
]
