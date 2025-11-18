"""
Base Platform Adapter
=====================
Abstract base class for all platform adapters.

All adapters MUST inherit from this class and implement required methods.
This ensures consistent, compliant integrations across all platforms.

COMPLIANCE REQUIREMENTS:
- Only use official APIs or approved methods (CSV, catalog, etc.)
- No browser automation unless explicitly allowed by platform TOS
- Respect rate limits
- Handle authentication securely
- Document compliance status
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
from ..schema.unified_listing import UnifiedListing


class IntegrationType(Enum):
    """Types of platform integrations"""
    API = "api"                    # Direct API integration (eBay, Etsy, Shopify)
    CSV_EXPORT = "csv_export"      # CSV file generation (Poshmark, Bonanza)
    FEED = "feed"                  # Product feed/catalog (Facebook, Google Shopping)
    TEMPLATE = "template"          # Manual posting template (Craigslist)
    MANUAL = "manual"              # No automation, user handles entirely


class ComplianceStatus(Enum):
    """Compliance status of adapter"""
    COMPLIANT = "compliant"        # ✅ Fully TOS-compliant
    WARNING = "warning"            # ⚠️ Requires manual steps
    NON_COMPLIANT = "non_compliant"  # ❌ Violates TOS (should not exist)


class PlatformAdapter(ABC):
    """
    Abstract base class for all platform adapters.

    All platform integrations must inherit from this class.
    """

    def __init__(self):
        """Initialize adapter"""
        self.platform_name = self.get_platform_name()
        self.integration_type = self.get_integration_type()
        self.compliance_status = self.get_compliance_status()

    @abstractmethod
    def get_platform_name(self) -> str:
        """
        Get the platform name.

        Returns:
            Platform name (e.g., "eBay", "Etsy", "Poshmark")
        """
        pass

    @abstractmethod
    def get_integration_type(self) -> IntegrationType:
        """
        Get the integration type.

        Returns:
            IntegrationType enum value
        """
        pass

    @abstractmethod
    def get_compliance_status(self) -> ComplianceStatus:
        """
        Get compliance status.

        Returns:
            ComplianceStatus enum value
        """
        pass

    @abstractmethod
    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        """
        Validate platform credentials.

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, "error message") if invalid
        """
        pass

    @abstractmethod
    def convert_to_platform_format(self, listing: UnifiedListing) -> Dict[str, Any]:
        """
        Convert UnifiedListing to platform-specific format.

        Args:
            listing: UnifiedListing object

        Returns:
            Platform-specific listing data

        Raises:
            ValueError: If listing data is invalid
        """
        pass

    @abstractmethod
    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        """
        Publish listing to platform.

        For API integrations: Makes API call
        For CSV exports: Generates CSV file
        For feeds: Adds to feed
        For templates: Generates template

        Args:
            listing: UnifiedListing object

        Returns:
            Dictionary with results:
            {
                "success": bool,
                "listing_id": str (if applicable),
                "listing_url": str (if applicable),
                "file_path": str (for CSV/template),
                "message": str,
                "error": str (if failed)
            }

        Raises:
            Exception: If publishing fails
        """
        pass

    def get_rate_limits(self) -> Dict[str, int]:
        """
        Get rate limits for this platform.

        Returns:
            Dictionary with rate limit info:
            {
                "requests_per_second": int,
                "requests_per_minute": int,
                "requests_per_hour": int,
                "requests_per_day": int,
            }
        """
        return {
            "requests_per_second": None,
            "requests_per_minute": None,
            "requests_per_hour": None,
            "requests_per_day": None,
        }

    def get_supported_features(self) -> Dict[str, bool]:
        """
        Get supported features for this platform.

        Returns:
            Dictionary of supported features:
            {
                "multiple_photos": bool,
                "variations": bool,  # Size/color variants
                "bulk_upload": bool,
                "scheduled_posting": bool,
                "auto_relist": bool,
                "inventory_sync": bool,
            }
        """
        return {
            "multiple_photos": False,
            "variations": False,
            "bulk_upload": False,
            "scheduled_posting": False,
            "auto_relist": False,
            "inventory_sync": False,
        }

    def get_photo_requirements(self) -> Dict[str, Any]:
        """
        Get photo requirements for this platform.

        Returns:
            Dictionary with photo requirements:
            {
                "max_photos": int,
                "min_photos": int,
                "max_file_size_mb": float,
                "supported_formats": List[str],
                "min_width": int,
                "min_height": int,
                "aspect_ratio": str (e.g., "1:1", "4:3"),
            }
        """
        return {
            "max_photos": 12,
            "min_photos": 1,
            "max_file_size_mb": 10.0,
            "supported_formats": ["jpg", "jpeg", "png"],
            "min_width": 500,
            "min_height": 500,
            "aspect_ratio": None,
        }

    def get_listing_requirements(self) -> Dict[str, Any]:
        """
        Get listing requirements for this platform.

        Returns:
            Dictionary with listing requirements:
            {
                "title_max_length": int,
                "description_max_length": int,
                "required_fields": List[str],
                "supported_conditions": List[str],
            }
        """
        return {
            "title_max_length": 80,
            "description_max_length": 5000,
            "required_fields": ["title", "price", "description", "photos"],
            "supported_conditions": ["new", "like_new", "good", "fair", "poor"],
        }

    def get_tos_documentation_url(self) -> Optional[str]:
        """
        Get URL to platform's Terms of Service.

        Returns:
            URL to TOS documentation
        """
        return None

    def get_api_documentation_url(self) -> Optional[str]:
        """
        Get URL to platform's API documentation.

        Returns:
            URL to API documentation
        """
        return None

    def validate_listing(self, listing: UnifiedListing) -> tuple[bool, List[str]]:
        """
        Validate listing against platform requirements.

        Args:
            listing: UnifiedListing object

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        requirements = self.get_listing_requirements()
        photo_reqs = self.get_photo_requirements()

        # Validate title length
        if len(listing.title) > requirements["title_max_length"]:
            errors.append(
                f"Title exceeds maximum length of {requirements['title_max_length']} characters"
            )

        # Validate description length
        if len(listing.description) > requirements["description_max_length"]:
            errors.append(
                f"Description exceeds maximum length of {requirements['description_max_length']} characters"
            )

        # Validate photos
        if len(listing.photos) < photo_reqs["min_photos"]:
            errors.append(
                f"Minimum {photo_reqs['min_photos']} photo(s) required"
            )

        if len(listing.photos) > photo_reqs["max_photos"]:
            errors.append(
                f"Maximum {photo_reqs['max_photos']} photos allowed"
            )

        return (len(errors) == 0, errors)

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"{self.__class__.__name__}("
            f"platform={self.platform_name}, "
            f"type={self.integration_type.value}, "
            f"compliance={self.compliance_status.value})"
        )


class APIAdapter(PlatformAdapter):
    """
    Base class for API-based integrations.

    Use this for platforms with official REST APIs.
    Examples: eBay, Etsy, Shopify
    """

    def get_integration_type(self) -> IntegrationType:
        return IntegrationType.API

    def get_compliance_status(self) -> ComplianceStatus:
        return ComplianceStatus.COMPLIANT

    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers"""
        pass

    @abstractmethod
    def _get_api_endpoint(self, endpoint: str) -> str:
        """Get full API endpoint URL"""
        pass


class CSVAdapter(PlatformAdapter):
    """
    Base class for CSV export integrations.

    Use this for platforms that support CSV bulk upload.
    Examples: Poshmark, Bonanza, Ecrater
    """

    def get_integration_type(self) -> IntegrationType:
        return IntegrationType.CSV_EXPORT

    def get_compliance_status(self) -> ComplianceStatus:
        return ComplianceStatus.WARNING  # User must upload CSV manually

    @abstractmethod
    def generate_csv(self, listings: List[UnifiedListing]) -> str:
        """
        Generate CSV file from listings.

        Args:
            listings: List of UnifiedListing objects

        Returns:
            Path to generated CSV file
        """
        pass

    @abstractmethod
    def get_csv_headers(self) -> List[str]:
        """Get CSV column headers"""
        pass


class FeedAdapter(PlatformAdapter):
    """
    Base class for product feed/catalog integrations.

    Use this for platforms that use product feeds.
    Examples: Facebook Shops, Google Shopping, Pinterest
    """

    def get_integration_type(self) -> IntegrationType:
        return IntegrationType.FEED

    def get_compliance_status(self) -> ComplianceStatus:
        return ComplianceStatus.COMPLIANT

    @abstractmethod
    def generate_feed(self, listings: List[UnifiedListing], format: str = "csv") -> str:
        """
        Generate product feed.

        Args:
            listings: List of UnifiedListing objects
            format: Feed format ("csv", "xml", "json")

        Returns:
            Path to generated feed file
        """
        pass

    @abstractmethod
    def upload_feed(self, feed_path: str) -> Dict[str, Any]:
        """
        Upload feed to platform.

        Args:
            feed_path: Path to feed file

        Returns:
            Upload result dictionary
        """
        pass


class TemplateAdapter(PlatformAdapter):
    """
    Base class for template-based integrations.

    Use this for platforms with no API that require manual posting.
    Examples: Craigslist, VarageSale
    """

    def get_integration_type(self) -> IntegrationType:
        return IntegrationType.TEMPLATE

    def get_compliance_status(self) -> ComplianceStatus:
        return ComplianceStatus.WARNING  # User must post manually

    @abstractmethod
    def generate_template(self, listing: UnifiedListing) -> Dict[str, str]:
        """
        Generate listing template.

        Args:
            listing: UnifiedListing object

        Returns:
            Dictionary with template components:
            {
                "title": str,
                "description": str,
                "formatted_text": str,  # Formatted for copy/paste
                "email_body": str (if applicable),
            }
        """
        pass

    def publish_listing(self, listing: UnifiedListing) -> Dict[str, Any]:
        """
        Generate template (does not actually post).

        Args:
            listing: UnifiedListing object

        Returns:
            Dictionary with template and instructions
        """
        template = self.generate_template(listing)

        return {
            "success": True,
            "message": f"Template generated for {self.platform_name}. Please post manually.",
            "template": template,
            "requires_manual_action": True,
        }
