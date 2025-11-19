"""
AI Cross-Poster
===============
Analyzes images to create optimized listings on multiple resell platforms.

Main components:
- schema: Unified listing schema
- adapters: Platform-specific adapters (eBay, Mercari)
- enhancer: AI-powered listing enhancement
- publisher: Cross-platform publishing orchestrator
- collectibles: Collectible recognition and attribute detection
- database: SQLite database for collectibles and listings
- sync: Multi-platform synchronization and auto-cancellation
- notifications: Email alerts for sales, offers, and failures
- shopping: Database lookup for shopping mode
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

# Adapters are imported on-demand to avoid missing module errors
# from .adapters import (
#     EbayAdapter,
#     MercariAdapter,
# )

# Enhancer and other modules imported on-demand
# from .enhancer import (
#     AIEnhancer,
#     enhance_listing,
# )

# Publisher imported on-demand
# from .publisher import (
#     CrossPlatformPublisher,
#     PublishResult,
#     publish_to_ebay,
#     publish_to_mercari,
#     publish_to_all,
# )

# Collectibles imported on-demand
# from .collectibles import (
#     CollectibleRecognizer,
#     identify_collectible,
#     AttributeDetector,
#     detect_attributes,
# )

from .database import (
    Database,
    get_db,
)

# Sync imported on-demand
# from .sync import (
#     MultiPlatformSyncManager,
# )

# Notifications imported on-demand
# from .notifications import (
#     NotificationManager,
# )

# Shopping imported on-demand
# from .shopping import (
#     ShoppingLookup,
#     quick_lookup,
#     profit_calculator,
#     compare_prices,
# )

__version__ = "2.0.0"  # Major update with collectibles and sync features

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
    # Database (always available)
    "Database",
    "get_db",
    # Other modules available via explicit imports:
    # from src.adapters import EbayAdapter, MercariAdapter
    # from src.enhancer import AIEnhancer, enhance_listing
    # from src.publisher import CrossPlatformPublisher, PublishResult, etc.
    # from src.collectibles import CollectibleRecognizer, AttributeDetector, etc.
    # from src.sync import MultiPlatformSyncManager
    # from src.notifications import NotificationManager
    # from src.shopping import ShoppingLookup, quick_lookup, etc.
]
