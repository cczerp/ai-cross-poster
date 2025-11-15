"""
Cross-Platform Publisher
========================
The main orchestrator that publishes listings to all platforms.

Provides:
- publish_to_all(listing): Publish to all configured platforms
- publish_to_ebay(listing): Publish to eBay only
- publish_to_mercari(listing): Publish to Mercari only
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import os
from datetime import datetime

from ..schema.unified_listing import UnifiedListing
from ..adapters.ebay_adapter import EbayAdapter
from ..adapters.mercari_adapter import MercariAdapter
from ..enhancer.ai_enhancer import AIEnhancer


@dataclass
class PublishResult:
    """Result of publishing to a platform"""

    platform: str
    success: bool
    listing_id: Optional[str] = None
    listing_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CrossPlatformPublisher:
    """
    Main publisher that coordinates publishing to all platforms.

    Handles:
    - Platform adapter initialization
    - AI enhancement (optional)
    - Multi-platform publishing
    - Error handling and rollback
    - Publishing history
    """

    def __init__(
        self,
        ebay_adapter: Optional[EbayAdapter] = None,
        mercari_adapter: Optional[MercariAdapter] = None,
        ai_enhancer: Optional[AIEnhancer] = None,
        auto_enhance: bool = True,
    ):
        """
        Initialize cross-platform publisher.

        Args:
            ebay_adapter: eBay adapter instance (None to disable eBay)
            mercari_adapter: Mercari adapter instance (None to disable Mercari)
            ai_enhancer: AI enhancer instance (None to disable AI enhancement)
            auto_enhance: Automatically enhance listings before publishing
        """
        self.ebay_adapter = ebay_adapter
        self.mercari_adapter = mercari_adapter
        self.ai_enhancer = ai_enhancer
        self.auto_enhance = auto_enhance

        # Track publishing history
        self.publish_history: List[Dict[str, Any]] = []

    def enhance_listing(
        self,
        listing: UnifiedListing,
        target_platform: str = "general",
        force: bool = False,
    ) -> UnifiedListing:
        """
        Enhance listing with AI if configured.

        Args:
            listing: Listing to enhance
            target_platform: Target platform for optimization
            force: Force enhancement even if already enhanced

        Returns:
            Enhanced listing
        """
        if not self.ai_enhancer:
            return listing

        if not self.auto_enhance and not force:
            return listing

        return self.ai_enhancer.enhance_listing(listing, target_platform, force)

    def publish_to_ebay(
        self,
        listing: UnifiedListing,
        enhance: bool = None,
    ) -> PublishResult:
        """
        Publish listing to eBay.

        Args:
            listing: Listing to publish
            enhance: Override auto_enhance setting

        Returns:
            PublishResult with eBay listing details
        """
        if not self.ebay_adapter:
            return PublishResult(
                platform="eBay",
                success=False,
                error="eBay adapter not configured",
            )

        try:
            # Enhance if requested
            if enhance or (enhance is None and self.auto_enhance):
                listing = self.enhance_listing(listing, target_platform="ebay")

            # Publish to eBay
            result = self.ebay_adapter.publish_listing(listing)

            # Update listing metadata
            listing.published_to_ebay = True
            listing.ebay_listing_id = result.get("listing_id")

            publish_result = PublishResult(
                platform="eBay",
                success=True,
                listing_id=result.get("listing_id"),
                metadata=result,
            )

            # Record in history
            self._record_publish(listing, publish_result)

            return publish_result

        except Exception as e:
            error_result = PublishResult(
                platform="eBay",
                success=False,
                error=str(e),
            )
            self._record_publish(listing, error_result)
            return error_result

    def publish_to_mercari(
        self,
        listing: UnifiedListing,
        enhance: bool = None,
    ) -> PublishResult:
        """
        Publish listing to Mercari.

        Args:
            listing: Listing to publish
            enhance: Override auto_enhance setting

        Returns:
            PublishResult with Mercari listing details
        """
        if not self.mercari_adapter:
            return PublishResult(
                platform="Mercari",
                success=False,
                error="Mercari adapter not configured",
            )

        try:
            # Enhance if requested
            if enhance or (enhance is None and self.auto_enhance):
                listing = self.enhance_listing(listing, target_platform="mercari")

            # Publish to Mercari
            result = self.mercari_adapter.publish_listing(listing)

            # Update listing metadata
            listing.published_to_mercari = True
            listing.mercari_listing_id = result.get("listing_id")

            publish_result = PublishResult(
                platform="Mercari",
                success=True,
                listing_id=result.get("listing_id"),
                listing_url=result.get("listing_url"),
                metadata=result,
            )

            # Record in history
            self._record_publish(listing, publish_result)

            return publish_result

        except Exception as e:
            error_result = PublishResult(
                platform="Mercari",
                success=False,
                error=str(e),
            )
            self._record_publish(listing, error_result)
            return error_result

    def publish_to_all(
        self,
        listing: UnifiedListing,
        enhance: bool = None,
        platforms: Optional[List[str]] = None,
    ) -> Dict[str, PublishResult]:
        """
        Publish listing to all configured platforms.

        Args:
            listing: Listing to publish
            enhance: Override auto_enhance setting
            platforms: List of platforms to publish to (None = all configured)

        Returns:
            Dictionary mapping platform name to PublishResult
        """
        results = {}

        # Determine which platforms to publish to
        if platforms is None:
            platforms = []
            if self.ebay_adapter:
                platforms.append("ebay")
            if self.mercari_adapter:
                platforms.append("mercari")

        # Normalize platform names
        platforms = [p.lower() for p in platforms]

        # Publish to each platform
        if "ebay" in platforms:
            results["eBay"] = self.publish_to_ebay(listing, enhance)

        if "mercari" in platforms:
            results["Mercari"] = self.publish_to_mercari(listing, enhance)

        return results

    def _record_publish(
        self,
        listing: UnifiedListing,
        result: PublishResult,
    ):
        """Record publishing attempt in history"""
        self.publish_history.append({
            "timestamp": datetime.now().isoformat(),
            "platform": result.platform,
            "success": result.success,
            "listing_title": listing.title,
            "listing_id": result.listing_id,
            "error": result.error,
        })

    def get_publish_history(self) -> List[Dict[str, Any]]:
        """Get publishing history"""
        return self.publish_history

    def get_success_rate(self, platform: Optional[str] = None) -> float:
        """
        Calculate success rate for publishing.

        Args:
            platform: Specific platform (None for overall)

        Returns:
            Success rate as percentage (0-100)
        """
        history = self.publish_history
        if platform:
            history = [h for h in history if h["platform"].lower() == platform.lower()]

        if not history:
            return 0.0

        successes = sum(1 for h in history if h["success"])
        return (successes / len(history)) * 100

    @classmethod
    def from_env(cls, auto_enhance: bool = True) -> "CrossPlatformPublisher":
        """
        Create publisher from environment variables.

        Expected environment variables:
        - eBay: EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REFRESH_TOKEN
        - Mercari: MERCARI_API_KEY, MERCARI_SHOP_ID (or MERCARI_EMAIL, MERCARI_PASSWORD)
        - AI: OPENAI_API_KEY, ANTHROPIC_API_KEY

        Args:
            auto_enhance: Enable automatic AI enhancement

        Returns:
            Configured CrossPlatformPublisher
        """
        # Initialize eBay adapter if credentials available
        ebay_adapter = None
        try:
            ebay_adapter = EbayAdapter.from_env()
        except ValueError:
            print("⚠️  eBay adapter not configured (missing credentials)")

        # Initialize Mercari adapter if credentials available
        mercari_adapter = None
        try:
            mercari_adapter = MercariAdapter.from_env()
        except ValueError:
            print("⚠️  Mercari adapter not configured (missing credentials)")

        # Initialize AI enhancer if keys available
        ai_enhancer = None
        try:
            ai_enhancer = AIEnhancer.from_env()
        except ValueError:
            print("⚠️  AI enhancer not configured (missing API keys)")

        if not ebay_adapter and not mercari_adapter:
            raise ValueError(
                "At least one platform adapter must be configured. "
                "Please set environment variables for eBay or Mercari."
            )

        return cls(
            ebay_adapter=ebay_adapter,
            mercari_adapter=mercari_adapter,
            ai_enhancer=ai_enhancer,
            auto_enhance=auto_enhance,
        )


# Convenience functions for quick publishing
def publish_to_ebay(listing: UnifiedListing) -> PublishResult:
    """
    Quick function to publish to eBay using env credentials.

    Args:
        listing: Listing to publish

    Returns:
        PublishResult
    """
    publisher = CrossPlatformPublisher.from_env()
    return publisher.publish_to_ebay(listing)


def publish_to_mercari(listing: UnifiedListing) -> PublishResult:
    """
    Quick function to publish to Mercari using env credentials.

    Args:
        listing: Listing to publish

    Returns:
        PublishResult
    """
    publisher = CrossPlatformPublisher.from_env()
    return publisher.publish_to_mercari(listing)


def publish_to_all(listing: UnifiedListing) -> Dict[str, PublishResult]:
    """
    Quick function to publish to all platforms using env credentials.

    Args:
        listing: Listing to publish

    Returns:
        Dictionary of PublishResults by platform
    """
    publisher = CrossPlatformPublisher.from_env()
    return publisher.publish_to_all(listing)
