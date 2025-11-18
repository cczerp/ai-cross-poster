"""
Platform Field Mapper
=====================
Intelligent field mapping system that transforms UnifiedListing data
to match each platform's specific requirements.

This handles:
- Different field names across platforms
- Character limit variations
- Required vs optional fields
- Data format transformations
- Validation rules per platform

EXAMPLE:
    UnifiedListing.item_specifics.brand →
        Facebook: "brand"
        Etsy: "brand_name"
        Poshmark: "Brand"
        Square: "brand_id" (requires lookup)
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from ..schema.unified_listing import UnifiedListing, ListingCondition


class FieldType(Enum):
    """Type of field value"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ENUM = "enum"
    URL = "url"
    DATE = "date"


@dataclass
class FieldRule:
    """
    Rules for a platform-specific field.

    Defines how to extract, transform, and validate data.
    """
    # Field identification
    platform_field_name: str          # Name used by platform
    unified_field_path: str            # Path in UnifiedListing (dot notation)

    # Field properties
    field_type: FieldType
    required: bool = False
    default_value: Any = None

    # Constraints
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    pattern: Optional[str] = None

    # Transformations
    transform: Optional[Callable] = None  # Function to transform value

    # Validation
    validate: Optional[Callable] = None   # Custom validation function

    # Fallbacks
    fallback_paths: Optional[List[str]] = None  # Alternative paths to try


class PlatformFieldMapper:
    """
    Maps UnifiedListing fields to platform-specific formats.

    Each platform can define its own field mapping rules.
    """

    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.field_rules: Dict[str, FieldRule] = {}
        self.condition_map: Dict[ListingCondition, str] = {}

    def add_field_rule(self, rule: FieldRule):
        """Add a field mapping rule"""
        self.field_rules[rule.platform_field_name] = rule

    def set_condition_map(self, condition_map: Dict[ListingCondition, str]):
        """Set condition value mappings"""
        self.condition_map = condition_map

    def get_value_from_path(self, listing: UnifiedListing, path: str) -> Any:
        """
        Extract value from UnifiedListing using dot notation path.

        Example paths:
            "title" → listing.title
            "price.amount" → listing.price.amount
            "item_specifics.brand" → listing.item_specifics.brand
            "photos[0].url" → listing.photos[0].url
        """
        parts = path.split('.')
        value = listing

        for part in parts:
            # Handle array indexing
            if '[' in part:
                attr_name = part.split('[')[0]
                index = int(part.split('[')[1].split(']')[0])
                value = getattr(value, attr_name, None)
                if value and isinstance(value, list) and len(value) > index:
                    value = value[index]
                else:
                    return None
            else:
                value = getattr(value, part, None)

            if value is None:
                return None

        return value

    def transform_value(self, value: Any, rule: FieldRule) -> Any:
        """
        Transform value according to field rule.

        Handles:
        - Type conversion
        - String truncation
        - Custom transformations
        - Format conversions
        """
        if value is None:
            return rule.default_value

        # Apply custom transform if provided
        if rule.transform:
            value = rule.transform(value)

        # Type conversions
        if rule.field_type == FieldType.STRING:
            value = str(value)

            # Apply length constraints
            if rule.max_length and len(value) > rule.max_length:
                value = value[:rule.max_length]

        elif rule.field_type == FieldType.INTEGER:
            value = int(float(value))  # Handle "10.00" → 10

        elif rule.field_type == FieldType.FLOAT:
            value = float(value)

        elif rule.field_type == FieldType.BOOLEAN:
            if isinstance(value, str):
                value = value.lower() in ('true', 'yes', '1', 'on')
            else:
                value = bool(value)

        # Validate constraints
        if rule.allowed_values and value not in rule.allowed_values:
            value = rule.default_value

        if rule.min_value is not None and value < rule.min_value:
            value = rule.min_value

        if rule.max_value is not None and value > rule.max_value:
            value = rule.max_value

        # Custom validation
        if rule.validate and not rule.validate(value):
            value = rule.default_value

        return value

    def map_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        """
        Map UnifiedListing to platform-specific format.

        Args:
            listing: UnifiedListing object

        Returns:
            Dictionary with platform-specific field names and values

        Raises:
            ValueError: If required fields are missing
        """
        result = {}
        errors = []

        for platform_field, rule in self.field_rules.items():
            # Try primary path
            value = self.get_value_from_path(listing, rule.unified_field_path)

            # Try fallback paths if primary fails
            if value is None and rule.fallback_paths:
                for fallback_path in rule.fallback_paths:
                    value = self.get_value_from_path(listing, fallback_path)
                    if value is not None:
                        break

            # Transform value
            value = self.transform_value(value, rule)

            # Check required fields
            if rule.required and value is None:
                errors.append(
                    f"Required field '{platform_field}' is missing "
                    f"(path: {rule.unified_field_path})"
                )
                continue

            # Only include non-None values
            if value is not None:
                result[platform_field] = value

        if errors:
            raise ValueError(f"Field mapping errors: {'; '.join(errors)}")

        return result

    def map_condition(self, condition: ListingCondition) -> str:
        """Map UnifiedListing condition to platform-specific value"""
        return self.condition_map.get(
            condition,
            self.condition_map.get(ListingCondition.GOOD, "good")
        )

    def validate_mapped_data(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate mapped data against platform rules.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        for field_name, value in data.items():
            rule = self.field_rules.get(field_name)
            if not rule:
                continue

            # Check required
            if rule.required and value is None:
                errors.append(f"Required field '{field_name}' is missing")

            # Check length
            if isinstance(value, str):
                if rule.min_length and len(value) < rule.min_length:
                    errors.append(
                        f"Field '{field_name}' is too short "
                        f"(min {rule.min_length} chars)"
                    )
                if rule.max_length and len(value) > rule.max_length:
                    errors.append(
                        f"Field '{field_name}' is too long "
                        f"(max {rule.max_length} chars)"
                    )

            # Check value range
            if isinstance(value, (int, float)):
                if rule.min_value and value < rule.min_value:
                    errors.append(
                        f"Field '{field_name}' is too small "
                        f"(min {rule.min_value})"
                    )
                if rule.max_value and value > rule.max_value:
                    errors.append(
                        f"Field '{field_name}' is too large "
                        f"(max {rule.max_value})"
                    )

        return (len(errors) == 0, errors)


def create_photo_array_mapper(max_photos: int = 12, field_prefix: str = "Photo") -> Callable:
    """
    Create a function that maps photo array to individual fields.

    Used for CSV platforms that need "Photo 1", "Photo 2", etc.

    Args:
        max_photos: Maximum number of photos
        field_prefix: Prefix for photo fields ("Photo", "Image", etc.)

    Returns:
        Function that maps listing to photo dictionary
    """
    def mapper(listing: UnifiedListing) -> Dict[str, str]:
        result = {}
        for i in range(max_photos):
            field_name = f"{field_prefix} {i + 1}"
            if i < len(listing.photos):
                photo = listing.photos[i]
                result[field_name] = photo.url or photo.local_path or ""
            else:
                result[field_name] = ""
        return result
    return mapper


def create_price_formatter(
    currency_symbol: bool = True,
    decimal_places: int = 2,
    thousands_separator: bool = False
) -> Callable:
    """
    Create a function that formats price values.

    Args:
        currency_symbol: Include $ symbol
        decimal_places: Number of decimal places
        thousands_separator: Include comma separator

    Returns:
        Function that formats price
    """
    def formatter(price_value: float) -> str:
        if thousands_separator:
            formatted = f"{price_value:,.{decimal_places}f}"
        else:
            formatted = f"{price_value:.{decimal_places}f}"

        if currency_symbol:
            return f"${formatted}"
        return formatted

    return formatter


def create_tag_joiner(separator: str = ", ", max_tags: int = None) -> Callable:
    """
    Create a function that joins array of tags into string.

    Args:
        separator: String to join tags with
        max_tags: Maximum number of tags to include

    Returns:
        Function that joins tags
    """
    def joiner(tags: List[str]) -> str:
        if not tags:
            return ""
        if max_tags:
            tags = tags[:max_tags]
        return separator.join(tags)

    return joiner


# Common field transformers
def truncate_string(max_length: int) -> Callable:
    """Create function that truncates string to max length"""
    def truncate(value: str) -> str:
        return value[:max_length] if value else ""
    return truncate


def convert_to_cents(value: float) -> int:
    """Convert dollar amount to cents (for Stripe, Square, etc.)"""
    return int(value * 100)


def boolean_to_string(true_value: str = "Yes", false_value: str = "No") -> Callable:
    """Convert boolean to string representation"""
    def converter(value: bool) -> str:
        return true_value if value else false_value
    return converter


def extract_primary_category(value: Any) -> str:
    """Extract primary category from Category object"""
    if hasattr(value, 'primary'):
        return value.primary or ""
    return str(value) if value else ""


def extract_all_photo_urls(listing: UnifiedListing) -> List[str]:
    """Extract all photo URLs from listing"""
    urls = []
    for photo in listing.photos:
        if photo.url:
            urls.append(photo.url)
        elif photo.local_path:
            urls.append(photo.local_path)
    return urls


def extract_primary_photo_url(listing: UnifiedListing) -> str:
    """Extract primary photo URL"""
    primary = listing.get_primary_photo()
    if primary:
        return primary.url or primary.local_path or ""
    return ""
