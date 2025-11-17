"""
Unified Listing Schema
======================
A single structured object that contains everything needed for both eBay and Mercari.
This prevents branching logic and ensures consistency across platforms.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class ListingCondition(Enum):
    """Standardized condition values that map to platform-specific conditions"""
    NEW = "new"
    NEW_WITH_TAGS = "new_with_tags"
    NEW_WITHOUT_TAGS = "new_without_tags"
    LIKE_NEW = "like_new"
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    FOR_PARTS = "for_parts"


class ListingFormat(Enum):
    """Listing format type"""
    FIXED_PRICE = "fixed_price"
    AUCTION = "auction"


class ShippingService(Enum):
    """Shipping service options"""
    STANDARD = "standard"
    EXPEDITED = "expedited"
    OVERNIGHT = "overnight"
    ECONOMY = "economy"
    FREE = "free"


@dataclass
class Photo:
    """Individual photo with metadata"""
    url: str
    local_path: Optional[str] = None
    order: int = 0
    ai_analysis: Optional[str] = None  # AI-generated description of photo
    is_primary: bool = False


@dataclass
class Dimensions:
    """Package/item dimensions"""
    length: Optional[float] = None  # inches
    width: Optional[float] = None   # inches
    height: Optional[float] = None  # inches
    weight: Optional[float] = None  # pounds

    def is_complete(self) -> bool:
        """Check if all dimensions are provided"""
        return all([self.length, self.width, self.height, self.weight])


@dataclass
class Price:
    """Pricing information"""
    amount: float
    currency: str = "USD"
    compare_at_price: Optional[float] = None  # Original/MSRP price for discounts
    minimum_acceptable: Optional[float] = None  # For offers/auctions


@dataclass
class Shipping:
    """Shipping configuration"""
    service: ShippingService = ShippingService.STANDARD
    cost: Optional[float] = None  # None = free shipping
    ships_from_zip: Optional[str] = None
    handling_time_days: int = 3
    domestic_only: bool = True
    package_dimensions: Optional[Dimensions] = None


@dataclass
class Category:
    """Platform-agnostic category information"""
    primary: str
    subcategory: Optional[str] = None
    ebay_category_id: Optional[str] = None
    mercari_category_id: Optional[str] = None
    suggested_keywords: List[str] = field(default_factory=list)


@dataclass
class ItemSpecifics:
    """Detailed item attributes (brand, size, color, etc.)"""
    brand: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    style: Optional[str] = None
    model: Optional[str] = None
    upc: Optional[str] = None
    isbn: Optional[str] = None
    mpn: Optional[str] = None  # Manufacturer Part Number
    custom_attributes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for platform adapters"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None and key != 'custom_attributes':
                result[key] = str(value)
        result.update(self.custom_attributes)
        return result


@dataclass
class SEOData:
    """SEO and search optimization data"""
    keywords: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    search_terms: List[str] = field(default_factory=list)
    optimized_title: Optional[str] = None  # AI-enhanced title


@dataclass
class UnifiedListing:
    """
    The master listing schema that works for both eBay and Mercari.

    Required fields:
        - title: Item title (80 chars for eBay, 40 for Mercari - will be adapted)
        - description: Full item description
        - price: Price object
        - condition: Standardized condition
        - photos: List of photos (12 max for eBay, 10 for Mercari)

    High-impact optional fields:
        - item_specifics: Brand, size, color, etc. (crucial for search)
        - category: Proper categorization
        - seo_data: Keywords and search optimization
    """

    # Core required fields
    title: str
    description: str
    price: Price
    condition: ListingCondition
    photos: List[Photo]

    # High-impact optional fields
    item_specifics: ItemSpecifics = field(default_factory=ItemSpecifics)
    category: Optional[Category] = None
    seo_data: SEOData = field(default_factory=SEOData)
    shipping: Shipping = field(default_factory=Shipping)

    # Listing configuration
    listing_format: ListingFormat = ListingFormat.FIXED_PRICE
    quantity: int = 1
    duration_days: Optional[int] = None  # None = Good 'til Cancelled

    # Optional metadata
    sku: Optional[str] = None
    location: Optional[str] = None
    storage_location: Optional[str] = None  # Physical storage location (e.g., "A1", "B2")
    returns_accepted: bool = True
    return_period_days: int = 30

    # AI Enhancement tracking
    ai_enhanced: bool = False
    ai_enhancement_timestamp: Optional[datetime] = None
    ai_provider: Optional[str] = None  # e.g., "OpenAI", "Anthropic"

    # Platform-specific overrides (use sparingly)
    ebay_overrides: Dict[str, Any] = field(default_factory=dict)
    mercari_overrides: Dict[str, Any] = field(default_factory=dict)

    # Publishing tracking
    published_to_ebay: bool = False
    published_to_mercari: bool = False
    ebay_listing_id: Optional[str] = None
    mercari_listing_id: Optional[str] = None

    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate the listing data.
        Returns (is_valid, list_of_errors)
        """
        errors = []

        # Title validation
        if not self.title or len(self.title.strip()) == 0:
            errors.append("Title is required")
        elif len(self.title) > 80:
            errors.append("Title exceeds 80 characters (eBay limit)")

        # Description validation
        if not self.description or len(self.description.strip()) == 0:
            errors.append("Description is required")

        # Price validation
        if self.price.amount <= 0:
            errors.append("Price must be greater than 0")

        # Photos validation
        if not self.photos or len(self.photos) == 0:
            errors.append("At least one photo is required")
        elif len(self.photos) > 12:
            errors.append("Too many photos (max 12 for eBay)")

        # Check for primary photo
        if self.photos and not any(p.is_primary for p in self.photos):
            errors.append("No primary photo designated")

        # Quantity validation
        if self.quantity < 1:
            errors.append("Quantity must be at least 1")

        return (len(errors) == 0, errors)

    def get_platform_title(self, platform: str) -> str:
        """Get title optimized for specific platform"""
        if platform.lower() == "mercari" and len(self.title) > 40:
            # Truncate for Mercari's 40-char limit
            return self.title[:37] + "..."
        return self.title

    def get_primary_photo(self) -> Optional[Photo]:
        """Get the primary photo"""
        for photo in self.photos:
            if photo.is_primary:
                return photo
        return self.photos[0] if self.photos else None

    def get_platform_photos(self, platform: str) -> List[Photo]:
        """Get photos limited for specific platform"""
        max_photos = 10 if platform.lower() == "mercari" else 12
        return self.photos[:max_photos]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "title": self.title,
            "description": self.description,
            "price": {
                "amount": self.price.amount,
                "currency": self.price.currency,
                "compare_at_price": self.price.compare_at_price,
                "minimum_acceptable": self.price.minimum_acceptable,
            },
            "condition": self.condition.value,
            "photos": [{"url": p.url, "order": p.order, "is_primary": p.is_primary} for p in self.photos],
            "item_specifics": self.item_specifics.to_dict(),
            "category": {
                "primary": self.category.primary,
                "subcategory": self.category.subcategory,
            } if self.category else None,
            "seo_data": {
                "keywords": self.seo_data.keywords,
                "hashtags": self.seo_data.hashtags,
            },
            "listing_format": self.listing_format.value,
            "quantity": self.quantity,
            "sku": self.sku,
            "storage_location": self.storage_location,
            "published_to_ebay": self.published_to_ebay,
            "published_to_mercari": self.published_to_mercari,
        }
