"""
Platform Configurations
=======================
Field mapping configurations for all 17 supported platforms.

Each platform defines:
- Field names and paths
- Data type requirements
- Validation rules
- Transformation functions
- Condition mappings

This centralizes all platform-specific quirks in one place.
"""

from .field_mapper import (
    PlatformFieldMapper,
    FieldRule,
    FieldType,
    create_price_formatter,
    create_photo_array_mapper,
    truncate_string,
    convert_to_cents,
    extract_primary_category,
)
from ..schema.unified_listing import ListingCondition


# ============================================================================
# ETSY
# ============================================================================

def create_etsy_mapper() -> PlatformFieldMapper:
    """
    Etsy API v3 field mapping.

    API: https://developers.etsy.com/documentation/reference#tag/ShopListing
    """
    mapper = PlatformFieldMapper("Etsy")

    # Required fields
    mapper.add_field_rule(FieldRule(
        platform_field_name="title",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
        max_length=140,  # Etsy limit
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="description",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=True,
        max_length=5000,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="price",
        unified_field_path="price.amount",
        field_type=FieldType.FLOAT,
        required=True,
        min_value=0.20,  # Etsy minimum
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="quantity",
        unified_field_path="quantity",
        field_type=FieldType.INTEGER,
        required=True,
        default_value=1,
        min_value=0,
        max_value=999,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="who_made",
        unified_field_path="item_specifics.custom_attributes.who_made",
        field_type=FieldType.ENUM,
        required=True,
        allowed_values=["i_did", "someone_else", "collective"],
        default_value="someone_else",
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="when_made",
        unified_field_path="item_specifics.custom_attributes.when_made",
        field_type=FieldType.ENUM,
        required=True,
        allowed_values=[
            "made_to_order", "2020_2024", "2010_2019", "2000_2009",
            "1990s", "1980s", "1970s", "1960s", "1950s", "1940s",
            "1930s", "1920s", "1910s", "1900s", "1800s", "1700s",
            "before_1700"
        ],
        default_value="2020_2024",
    ))

    # Optional fields
    mapper.add_field_rule(FieldRule(
        platform_field_name="tags",
        unified_field_path="seo_data.keywords",
        field_type=FieldType.ARRAY,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="materials",
        unified_field_path="item_specifics.material",
        field_type=FieldType.ARRAY,
        required=False,
    ))

    # Condition mapping
    mapper.set_condition_map({
        ListingCondition.NEW: "new",
        ListingCondition.NEW_WITH_TAGS: "new",
        ListingCondition.NEW_WITHOUT_TAGS: "new",
        ListingCondition.LIKE_NEW: "like_new",
        ListingCondition.EXCELLENT: "good",
        ListingCondition.GOOD: "good",
        ListingCondition.FAIR: "acceptable",
        ListingCondition.POOR: "acceptable",
    })

    return mapper


# ============================================================================
# SHOPIFY
# ============================================================================

def create_shopify_mapper() -> PlatformFieldMapper:
    """
    Shopify Admin API field mapping.

    API: https://shopify.dev/api/admin-rest/2024-01/resources/product
    """
    mapper = PlatformFieldMapper("Shopify")

    mapper.add_field_rule(FieldRule(
        platform_field_name="title",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
        max_length=255,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="body_html",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="vendor",
        unified_field_path="item_specifics.brand",
        field_type=FieldType.STRING,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="product_type",
        unified_field_path="category.primary",
        field_type=FieldType.STRING,
        required=False,
        transform=extract_primary_category,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="tags",
        unified_field_path="seo_data.keywords",
        field_type=FieldType.ARRAY,
        required=False,
    ))

    # Variants (Shopify requires at least one variant)
    mapper.add_field_rule(FieldRule(
        platform_field_name="price",
        unified_field_path="price.amount",
        field_type=FieldType.FLOAT,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="compare_at_price",
        unified_field_path="price.compare_at_price",
        field_type=FieldType.FLOAT,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="sku",
        unified_field_path="sku",
        field_type=FieldType.STRING,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="inventory_quantity",
        unified_field_path="quantity",
        field_type=FieldType.INTEGER,
        default_value=1,
    ))

    return mapper


# ============================================================================
# POSHMARK (CSV)
# ============================================================================

def create_poshmark_mapper() -> PlatformFieldMapper:
    """
    Poshmark CSV bulk upload field mapping.

    Format: https://poshmark.com/sell/bulk
    """
    mapper = PlatformFieldMapper("Poshmark")

    mapper.add_field_rule(FieldRule(
        platform_field_name="Title",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
        max_length=80,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Description",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=True,
        max_length=500,  # Poshmark limit
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Category",
        unified_field_path="category.primary",
        field_type=FieldType.STRING,
        required=True,
        transform=extract_primary_category,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Brand",
        unified_field_path="item_specifics.brand",
        field_type=FieldType.STRING,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Size",
        unified_field_path="item_specifics.size",
        field_type=FieldType.STRING,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Color",
        unified_field_path="item_specifics.color",
        field_type=FieldType.STRING,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Price",
        unified_field_path="price.amount",
        field_type=FieldType.STRING,
        required=True,
        transform=create_price_formatter(currency_symbol=True),
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Compare At Price",
        unified_field_path="price.compare_at_price",
        field_type=FieldType.STRING,
        required=False,
        transform=create_price_formatter(currency_symbol=True),
    ))

    # Condition mapping
    mapper.set_condition_map({
        ListingCondition.NEW: "NWT",
        ListingCondition.NEW_WITH_TAGS: "NWT",
        ListingCondition.NEW_WITHOUT_TAGS: "NWOT",
        ListingCondition.LIKE_NEW: "Like New",
        ListingCondition.EXCELLENT: "Excellent",
        ListingCondition.GOOD: "Good",
        ListingCondition.FAIR: "Fair",
        ListingCondition.POOR: "Poor",
    })

    return mapper


# ============================================================================
# FACEBOOK SHOPS (Product Feed)
# ============================================================================

def create_facebook_mapper() -> PlatformFieldMapper:
    """
    Facebook Catalog product feed field mapping.

    Format: https://developers.facebook.com/docs/marketing-api/catalog/reference
    """
    mapper = PlatformFieldMapper("Facebook")

    mapper.add_field_rule(FieldRule(
        platform_field_name="id",
        unified_field_path="sku",
        field_type=FieldType.STRING,
        required=True,
        fallback_paths=["listing_uuid"],
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="title",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
        max_length=150,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="description",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=True,
        max_length=5000,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="availability",
        unified_field_path="quantity",
        field_type=FieldType.STRING,
        required=True,
        transform=lambda q: "in stock" if q > 0 else "out of stock",
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="condition",
        unified_field_path="condition",
        field_type=FieldType.STRING,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="price",
        unified_field_path="price.amount",
        field_type=FieldType.STRING,
        required=True,
        transform=lambda p: f"{p:.2f} USD",
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="link",
        unified_field_path="item_specifics.custom_attributes.product_url",
        field_type=FieldType.URL,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="image_link",
        unified_field_path="photos[0].url",
        field_type=FieldType.URL,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="brand",
        unified_field_path="item_specifics.brand",
        field_type=FieldType.STRING,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="google_product_category",
        unified_field_path="category.primary",
        field_type=FieldType.STRING,
        required=False,
    ))

    # Condition mapping
    mapper.set_condition_map({
        ListingCondition.NEW: "new",
        ListingCondition.NEW_WITH_TAGS: "new",
        ListingCondition.NEW_WITHOUT_TAGS: "new",
        ListingCondition.LIKE_NEW: "refurbished",
        ListingCondition.EXCELLENT: "used",
        ListingCondition.GOOD: "used",
        ListingCondition.FAIR: "used",
        ListingCondition.POOR: "used",
    })

    return mapper


# ============================================================================
# GOOGLE SHOPPING (Product Feed)
# ============================================================================

def create_google_shopping_mapper() -> PlatformFieldMapper:
    """
    Google Merchant Center product feed field mapping.

    Format: https://support.google.com/merchants/answer/7052112
    """
    mapper = PlatformFieldMapper("Google Shopping")

    mapper.add_field_rule(FieldRule(
        platform_field_name="id",
        unified_field_path="sku",
        field_type=FieldType.STRING,
        required=True,
        fallback_paths=["listing_uuid"],
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="title",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
        max_length=150,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="description",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=True,
        max_length=5000,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="link",
        unified_field_path="item_specifics.custom_attributes.product_url",
        field_type=FieldType.URL,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="image_link",
        unified_field_path="photos[0].url",
        field_type=FieldType.URL,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="availability",
        unified_field_path="quantity",
        field_type=FieldType.STRING,
        required=True,
        transform=lambda q: "in_stock" if q > 0 else "out_of_stock",
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="price",
        unified_field_path="price.amount",
        field_type=FieldType.STRING,
        required=True,
        transform=lambda p: f"{p:.2f} USD",
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="condition",
        unified_field_path="condition",
        field_type=FieldType.STRING,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="brand",
        unified_field_path="item_specifics.brand",
        field_type=FieldType.STRING,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="gtin",
        unified_field_path="item_specifics.upc",
        field_type=FieldType.STRING,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="mpn",
        unified_field_path="item_specifics.mpn",
        field_type=FieldType.STRING,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="google_product_category",
        unified_field_path="category.primary",
        field_type=FieldType.STRING,
        required=False,
    ))

    # Condition mapping
    mapper.set_condition_map({
        ListingCondition.NEW: "new",
        ListingCondition.NEW_WITH_TAGS: "new",
        ListingCondition.NEW_WITHOUT_TAGS: "new",
        ListingCondition.LIKE_NEW: "refurbished",
        ListingCondition.EXCELLENT: "used",
        ListingCondition.GOOD: "used",
        ListingCondition.FAIR: "used",
        ListingCondition.POOR: "used",
    })

    return mapper


# ============================================================================
# SQUARE (POS/E-commerce)
# ============================================================================

def create_square_mapper() -> PlatformFieldMapper:
    """
    Square Catalog API field mapping.

    API: https://developer.squareup.com/reference/square/catalog-api
    """
    mapper = PlatformFieldMapper("Square")

    mapper.add_field_rule(FieldRule(
        platform_field_name="name",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
        max_length=255,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="description",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=False,
        max_length=4096,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="price_money",
        unified_field_path="price.amount",
        field_type=FieldType.INTEGER,
        required=True,
        transform=convert_to_cents,  # Square uses cents
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="sku",
        unified_field_path="sku",
        field_type=FieldType.STRING,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="track_inventory",
        unified_field_path="quantity",
        field_type=FieldType.BOOLEAN,
        default_value=True,
        transform=lambda q: q is not None and q > 0,
    ))

    return mapper


# ============================================================================
# WOOCOMMERCE
# ============================================================================

def create_woocommerce_mapper() -> PlatformFieldMapper:
    """
    WooCommerce REST API field mapping.

    API: https://woocommerce.github.io/woocommerce-rest-api-docs/#products
    """
    mapper = PlatformFieldMapper("WooCommerce")

    mapper.add_field_rule(FieldRule(
        platform_field_name="name",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="description",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="regular_price",
        unified_field_path="price.amount",
        field_type=FieldType.STRING,
        required=True,
        transform=lambda p: str(p),
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="sale_price",
        unified_field_path="price.compare_at_price",
        field_type=FieldType.STRING,
        required=False,
        transform=lambda p: str(p) if p else None,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="sku",
        unified_field_path="sku",
        field_type=FieldType.STRING,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="stock_quantity",
        unified_field_path="quantity",
        field_type=FieldType.INTEGER,
        default_value=1,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="manage_stock",
        unified_field_path="quantity",
        field_type=FieldType.BOOLEAN,
        default_value=True,
        transform=lambda q: q is not None,
    ))

    return mapper


# ============================================================================
# PINTEREST
# ============================================================================

def create_pinterest_mapper() -> PlatformFieldMapper:
    """
    Pinterest Pins API field mapping.

    API: https://developers.pinterest.com/docs/api/v5/#tag/pins
    """
    mapper = PlatformFieldMapper("Pinterest")

    mapper.add_field_rule(FieldRule(
        platform_field_name="title",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
        max_length=100,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="description",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=False,
        max_length=500,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="link",
        unified_field_path="item_specifics.custom_attributes.product_url",
        field_type=FieldType.URL,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="media_source",
        unified_field_path="photos[0].url",
        field_type=FieldType.URL,
        required=True,
    ))

    return mapper


# ============================================================================
# DEPOP (API)
# ============================================================================

def create_depop_mapper() -> PlatformFieldMapper:
    """
    Depop API field mapping.

    Note: Depop API is available for approved sellers
    """
    mapper = PlatformFieldMapper("Depop")

    mapper.add_field_rule(FieldRule(
        platform_field_name="title",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
        max_length=65,  # Depop limit
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="description",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=True,
        max_length=1000,  # Depop limit
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="price",
        unified_field_path="price.amount",
        field_type=FieldType.FLOAT,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="brand",
        unified_field_path="item_specifics.brand",
        field_type=FieldType.STRING,
        required=False,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="size",
        unified_field_path="item_specifics.size",
        field_type=FieldType.STRING,
        required=False,
    ))

    # Condition mapping
    mapper.set_condition_map({
        ListingCondition.NEW: "Brand New",
        ListingCondition.NEW_WITH_TAGS: "Brand New",
        ListingCondition.LIKE_NEW: "Like New",
        ListingCondition.EXCELLENT: "Excellent",
        ListingCondition.GOOD: "Good",
        ListingCondition.FAIR: "Fair",
        ListingCondition.POOR: "Poor",
    })

    return mapper


# ============================================================================
# CSV PLATFORMS (Bonanza, Ecrater, Ruby Lane, OfferUp)
# ============================================================================

def create_bonanza_mapper() -> PlatformFieldMapper:
    """Bonanza CSV import field mapping"""
    mapper = PlatformFieldMapper("Bonanza")

    mapper.add_field_rule(FieldRule(
        platform_field_name="Title",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
        max_length=80,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Description",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Price",
        unified_field_path="price.amount",
        field_type=FieldType.FLOAT,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Quantity",
        unified_field_path="quantity",
        field_type=FieldType.INTEGER,
        default_value=1,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Category",
        unified_field_path="category.primary",
        field_type=FieldType.STRING,
        transform=extract_primary_category,
    ))

    return mapper


def create_ecrater_mapper() -> PlatformFieldMapper:
    """Ecrater CSV import field mapping"""
    mapper = PlatformFieldMapper("Ecrater")

    mapper.add_field_rule(FieldRule(
        platform_field_name="title",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="description",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="price",
        unified_field_path="price.amount",
        field_type=FieldType.FLOAT,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="quantity",
        unified_field_path="quantity",
        field_type=FieldType.INTEGER,
        default_value=1,
    ))

    return mapper


def create_rubylane_mapper() -> PlatformFieldMapper:
    """Ruby Lane CSV import field mapping"""
    mapper = PlatformFieldMapper("Ruby Lane")

    mapper.add_field_rule(FieldRule(
        platform_field_name="Item Title",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Description",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="Price",
        unified_field_path="price.amount",
        field_type=FieldType.FLOAT,
        required=True,
    ))

    return mapper


def create_offerup_mapper() -> PlatformFieldMapper:
    """OfferUp CSV export field mapping"""
    mapper = PlatformFieldMapper("OfferUp")

    mapper.add_field_rule(FieldRule(
        platform_field_name="title",
        unified_field_path="title",
        field_type=FieldType.STRING,
        required=True,
        max_length=80,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="description",
        unified_field_path="description",
        field_type=FieldType.STRING,
        required=True,
        max_length=1000,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="price",
        unified_field_path="price.amount",
        field_type=FieldType.FLOAT,
        required=True,
    ))

    mapper.add_field_rule(FieldRule(
        platform_field_name="category",
        unified_field_path="category.primary",
        field_type=FieldType.STRING,
        transform=extract_primary_category,
    ))

    return mapper


# ============================================================================
# Factory Function
# ============================================================================

def get_platform_mapper(platform_name: str) -> PlatformFieldMapper:
    """
    Get field mapper for a specific platform.

    Args:
        platform_name: Name of platform (case-insensitive)

    Returns:
        PlatformFieldMapper instance

    Raises:
        ValueError: If platform not found
    """
    platform_name_lower = platform_name.lower()

    mappers = {
        "etsy": create_etsy_mapper,
        "shopify": create_shopify_mapper,
        "poshmark": create_poshmark_mapper,
        "facebook": create_facebook_mapper,
        "facebook shops": create_facebook_mapper,
        "google shopping": create_google_shopping_mapper,
        "google": create_google_shopping_mapper,
        "square": create_square_mapper,
        "woocommerce": create_woocommerce_mapper,
        "pinterest": create_pinterest_mapper,
        "depop": create_depop_mapper,
        "bonanza": create_bonanza_mapper,
        "ecrater": create_ecrater_mapper,
        "ruby lane": create_rubylane_mapper,
        "rubylane": create_rubylane_mapper,
        "offerup": create_offerup_mapper,
    }

    creator_func = mappers.get(platform_name_lower)
    if not creator_func:
        raise ValueError(
            f"Platform '{platform_name}' not found. "
            f"Available: {', '.join(mappers.keys())}"
        )

    return creator_func()
