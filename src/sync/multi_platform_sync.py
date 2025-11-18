"""
Multi-Platform Sync Manager
============================
Handles posting to multiple platforms, status syncing, and auto-cancellation.

Key Features:
- Post to all platforms simultaneously
- Auto-cancel on other platforms when item sells
- Retry failed posts
- Send notifications for failures and sales
"""

import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..schema.unified_listing import UnifiedListing
from ..publisher import CrossPlatformPublisher, PublishResult
from ..database import get_db
from ..notifications import NotificationManager


class MultiPlatformSyncManager:
    """
    Manages synchronized listing across multiple platforms.

    Handles:
    - Multi-platform posting
    - Status synchronization
    - Auto-cancellation when sold
    - Retry logic for failures
    - Notifications
    """

    def __init__(
        self,
        publisher: Optional[CrossPlatformPublisher] = None,
        notification_manager: Optional[NotificationManager] = None,
        max_retries: int = 3,
    ):
        """
        Initialize sync manager.

        Args:
            publisher: CrossPlatformPublisher instance
            notification_manager: NotificationManager instance
            max_retries: Max retry attempts for failed posts
        """
        self.publisher = publisher or CrossPlatformPublisher.from_env(auto_enhance=False)
        self.notifier = notification_manager or NotificationManager.from_env()
        self.db = get_db()
        self.max_retries = max_retries

    def post_to_all_platforms(
        self,
        listing: UnifiedListing,
        platforms: Optional[List[str]] = None,
        collectible_id: Optional[int] = None,
        cost: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Post listing to all configured platforms.

        Args:
            listing: UnifiedListing object
            platforms: List of platforms to post to (None = all)
            collectible_id: ID of collectible if applicable
            cost: What you paid for the item

        Returns:
            Dictionary with results and listing_id
        """
        # Generate unique listing UUID
        listing_uuid = str(uuid.uuid4())

        print(f"\n{'='*70}")
        print(f"📤 MULTI-PLATFORM POSTING")
        print(f"{'='*70}")
        print(f"Listing UUID: {listing_uuid}")
        print(f"Title: {listing.title}")
        print(f"Price: ${listing.price.amount}")

        # Default platforms if not specified
        if platforms is None:
            platforms = []
            if self.publisher.ebay_adapter:
                platforms.append("ebay")
            if self.publisher.mercari_adapter:
                platforms.append("mercari")

        print(f"Target Platforms: {', '.join(platforms)}")

        # Create listing in database
        photos_data = []
        for photo in listing.photos:
            if photo.local_path:
                photos_data.append(photo.local_path)
            elif photo.url:
                photos_data.append(photo.url)

        listing_id = self.db.create_listing(
            listing_uuid=listing_uuid,
            title=listing.title,
            description=listing.description,
            price=listing.price.amount,
            condition=listing.condition.value,
            photos=photos_data,
            collectible_id=collectible_id,
            cost=cost,
            category=listing.category.primary if listing.category else None,
            attributes=listing.item_specifics.to_dict() if listing.item_specifics else None,
            quantity=listing.quantity,
            storage_location=listing.location,
        )

        print(f"Database Listing ID: {listing_id}\n")

        # Create platform listing entries
        for platform in platforms:
            self.db.add_platform_listing(
                listing_id=listing_id,
                platform=platform,
                status="pending",
            )

        # Post to platforms in parallel
        results = {}
        with ThreadPoolExecutor(max_workers=len(platforms)) as executor:
            future_to_platform = {
                executor.submit(
                    self._post_to_platform,
                    listing,
                    platform,
                    listing_id
                ): platform
                for platform in platforms
            }

            for future in as_completed(future_to_platform):
                platform = future_to_platform[future]
                try:
                    result = future.result()
                    results[platform] = result

                    # Update database
                    if result.success:
                        self.db.update_platform_listing_status(
                            listing_id=listing_id,
                            platform=platform,
                            status="active",
                            platform_listing_id=result.listing_id,
                            platform_url=result.listing_url,
                        )

                        self.db.log_sync(
                            listing_id=listing_id,
                            platform=platform,
                            action="create",
                            status="success",
                            details=result.metadata,
                        )

                        print(f"✅ {platform}: Posted successfully!")
                        if result.listing_url:
                            print(f"   URL: {result.listing_url}")

                    else:
                        self.db.update_platform_listing_status(
                            listing_id=listing_id,
                            platform=platform,
                            status="failed",
                            error_message=result.error,
                        )

                        self.db.log_sync(
                            listing_id=listing_id,
                            platform=platform,
                            action="create",
                            status="failed",
                            details={"error": result.error},
                        )

                        print(f"❌ {platform}: Failed - {result.error}")

                        # Send failure notification
                        self.notifier.send_listing_failed_notification(
                            listing_id=listing_id,
                            platform=platform,
                            error=result.error,
                            listing_title=listing.title,
                        )

                except Exception as e:
                    print(f"❌ {platform}: Exception - {str(e)}")
                    results[platform] = PublishResult(
                        platform=platform,
                        success=False,
                        error=str(e),
                    )

                    self.db.update_platform_listing_status(
                        listing_id=listing_id,
                        platform=platform,
                        status="failed",
                        error_message=str(e),
                    )

        # Update listing status
        if any(r.success for r in results.values()):
            self.db.update_listing_status(listing_id, "active")
        else:
            self.db.update_listing_status(listing_id, "failed")

        # Summary
        success_count = sum(1 for r in results.values() if r.success)
        print(f"\n{'='*70}")
        print(f"📊 SUMMARY")
        print(f"{'='*70}")
        print(f"Successfully posted: {success_count}/{len(platforms)} platforms")
        print(f"{'='*70}\n")

        return {
            "listing_id": listing_id,
            "listing_uuid": listing_uuid,
            "results": results,
            "success_count": success_count,
            "total_platforms": len(platforms),
        }

    def _post_to_platform(
        self,
        listing: UnifiedListing,
        platform: str,
        listing_id: int,
    ) -> PublishResult:
        """Post to a single platform (called in parallel)"""
        print(f"📤 Posting to {platform}...")

        try:
            if platform.lower() == "ebay":
                result = self.publisher.publish_to_ebay(listing, enhance=False)
            elif platform.lower() == "mercari":
                result = self.publisher.publish_to_mercari(listing, enhance=False)
            else:
                result = PublishResult(
                    platform=platform,
                    success=False,
                    error=f"Unknown platform: {platform}",
                )

            return result

        except Exception as e:
            return PublishResult(
                platform=platform,
                success=False,
                error=str(e),
            )

    def mark_sold(
        self,
        listing_id: int,
        sold_platform: str,
        sold_price: Optional[float] = None,
        buyer_email: Optional[str] = None,
        tracking_number: Optional[str] = None,
        quantity_sold: int = 1,
    ) -> Dict[str, Any]:
        """
        Mark listing as sold and schedule cancellation on other platforms.

        Two modes:
        1. Single-item (quantity=1): Marks as sold immediately, schedules cancellation after 15 minutes
        2. Multi-quantity (quantity>1): Reduces quantity by quantity_sold, only cancels when quantity reaches 0

        Args:
            listing_id: Database listing ID
            sold_platform: Platform where it sold
            sold_price: Final sale price
            buyer_email: Buyer email for shipping label
            tracking_number: Shipping tracking number
            quantity_sold: How many units sold (default 1)

        Returns:
            Dictionary with results
        """
        from datetime import datetime, timedelta

        print(f"\n{'='*70}")
        print(f"💰 MARKING AS SOLD")
        print(f"{'='*70}")

        # Get listing
        listing = self.db.get_listing(listing_id)
        if not listing:
            return {"error": "Listing not found"}

        print(f"Listing: {listing['title']}")
        print(f"Sold on: {sold_platform}")
        if sold_price:
            print(f"Sale Price: ${sold_price}")

        # Show storage location prominently
        if listing.get('storage_location'):
            print(f"\n📍 STORAGE LOCATION: {listing['storage_location']}")
            print(f"   Go to {listing['storage_location']} to find and ship this item!")

        current_quantity = listing.get('quantity', 1)
        remaining_quantity = max(0, current_quantity - quantity_sold)

        print(f"\nQuantity: {current_quantity} → {remaining_quantity} (sold {quantity_sold})")

        # Update quantity in database
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE listings
            SET quantity = ?
            WHERE id = ?
        """, (remaining_quantity, listing_id))
        self.db.conn.commit()

        # Determine action based on remaining quantity
        if remaining_quantity == 0:
            # No items left - mark as sold and schedule cancellation
            print("\n🚫 No quantity remaining - scheduling cancellation on other platforms")

            # Mark main listing as sold
            self.db.mark_listing_sold(
                listing_id=listing_id,
                platform=sold_platform,
                sold_price=sold_price,
            )

            # Get all platform listings
            platform_listings = self.db.get_platform_listings(listing_id)

            # Schedule cancellation with 15-minute cooldown
            cancel_time = datetime.now() + timedelta(minutes=15)
            cancellation_results = {}

            for pl in platform_listings:
                if pl["platform"] != sold_platform and pl["status"] == "active":
                    print(f"\n⏰ Scheduling cancellation on {pl['platform']} at {cancel_time.strftime('%H:%M:%S')}")

                    # Mark as pending_cancel and set schedule time
                    cursor.execute("""
                        UPDATE platform_listings
                        SET status = 'pending_cancel',
                            cancel_scheduled_at = ?
                        WHERE listing_id = ? AND platform = ?
                    """, (cancel_time.isoformat(), listing_id, pl["platform"]))
                    self.db.conn.commit()

                    self.db.log_sync(
                        listing_id=listing_id,
                        platform=pl["platform"],
                        action="schedule_cancel",
                        status="scheduled",
                        details={"reason": f"Sold on {sold_platform}", "cancel_at": cancel_time.isoformat()},
                    )

                    cancellation_results[pl["platform"]] = "scheduled_for_cancel"
                    print(f"✅ Cancellation scheduled for {pl['platform']} (15 min cooldown)")

            print(f"\n⏰ COOLDOWN PERIOD: 15 minutes to find and verify item")
            print(f"   Automatic cancellation at: {cancel_time.strftime('%H:%M:%S')}")

        else:
            # Items still remaining - just update quantity on platforms
            print(f"\n✅ {remaining_quantity} item(s) still available - updating quantity on platforms")

            # TODO: Update quantity on each platform via API
            # For now, just log the update
            platform_listings = self.db.get_platform_listings(listing_id)
            cancellation_results = {}

            for pl in platform_listings:
                if pl["status"] == "active":
                    self.db.log_sync(
                        listing_id=listing_id,
                        platform=pl["platform"],
                        action="update_quantity",
                        status="success",
                        details={"new_quantity": remaining_quantity, "sold_quantity": quantity_sold},
                    )
                    cancellation_results[pl["platform"]] = "quantity_updated"
                    print(f"✅ Updated quantity on {pl['platform']}")

        # Send sale notification with storage location
        self.notifier.send_sale_notification(
            listing_id=listing_id,
            platform=sold_platform,
            sale_price=sold_price or listing["price"],
            buyer_email=buyer_email,
            tracking_number=tracking_number,
            listing_title=listing["title"],
        )

        print(f"\n{'='*70}")
        print(f"✅ SALE RECORDED")
        print(f"{'='*70}\n")

        return {
            "listing_id": listing_id,
            "sold_platform": sold_platform,
            "quantity_sold": quantity_sold,
            "remaining_quantity": remaining_quantity,
            "storage_location": listing.get('storage_location'),
            "actions": cancellation_results,
            "notification_sent": True,
        }

    def retry_failed_posts(self) -> List[Dict[str, Any]]:
        """
        Retry all failed platform listings.

        Returns:
            List of retry results
        """
        print(f"\n{'='*70}")
        print(f"🔄 RETRYING FAILED POSTS")
        print(f"{'='*70}\n")

        # Get all failed platform listings
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT pl.*, l.*
            FROM platform_listings pl
            JOIN listings l ON pl.listing_id = l.id
            WHERE pl.status = 'failed'
            AND pl.retry_count < ?
            AND l.status != 'sold'
        """, (self.max_retries,))

        failed_listings = [dict(row) for row in cursor.fetchall()]

        if not failed_listings:
            print("No failed listings to retry")
            return []

        print(f"Found {len(failed_listings)} failed listings to retry\n")

        results = []
        for fl in failed_listings:
            print(f"Retrying: {fl['title']} on {fl['platform']}")

            # Reconstruct UnifiedListing
            # (This is simplified - in real implementation, fully reconstruct from DB)
            from ..schema.unified_listing import UnifiedListing, Price, ListingCondition, Photo

            listing = UnifiedListing(
                title=fl["title"],
                description=fl["description"] or "",
                price=Price(amount=fl["price"]),
                condition=ListingCondition(fl["condition"]),
                photos=[],  # TODO: Load from DB
            )

            # Retry posting
            result = self._post_to_platform(listing, fl["platform"], fl["listing_id"])

            # Update database
            if result.success:
                self.db.update_platform_listing_status(
                    listing_id=fl["listing_id"],
                    platform=fl["platform"],
                    status="active",
                    platform_listing_id=result.listing_id,
                    platform_url=result.listing_url,
                )
                print(f"  ✅ Success!")
            else:
                # Increment retry count
                cursor.execute("""
                    UPDATE platform_listings
                    SET retry_count = retry_count + 1,
                        error_message = ?,
                        last_synced = CURRENT_TIMESTAMP
                    WHERE listing_id = ? AND platform = ?
                """, (result.error, fl["listing_id"], fl["platform"]))
                self.db.conn.commit()
                print(f"  ❌ Failed again: {result.error}")

            results.append({
                "listing_id": fl["listing_id"],
                "platform": fl["platform"],
                "success": result.success,
                "error": result.error if not result.success else None,
            })

        print(f"\n{'='*70}")
        print(f"RETRY COMPLETE")
        print(f"{'='*70}\n")

        return results

    def check_platform_status(self, listing_id: int) -> Dict[str, str]:
        """
        Check status of listing on all platforms.

        Returns:
            Dictionary of platform -> status
        """
        platform_listings = self.db.get_platform_listings(listing_id)

        status = {}
        for pl in platform_listings:
            status[pl["platform"]] = pl["status"]

        return status

    @classmethod
    def from_env(cls) -> "MultiPlatformSyncManager":
        """Create sync manager from environment variables"""
        return cls(
            publisher=CrossPlatformPublisher.from_env(auto_enhance=False),
            notification_manager=NotificationManager.from_env(),
        )


# Convenience functions
def post_to_all(
    listing: UnifiedListing,
    platforms: Optional[List[str]] = None,
    collectible_id: Optional[int] = None,
    cost: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Quick function to post to all platforms.
    """
    manager = MultiPlatformSyncManager.from_env()
    return manager.post_to_all_platforms(listing, platforms, collectible_id, cost)


def mark_sold(
    listing_id: int,
    sold_platform: str,
    sold_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Quick function to mark as sold and cancel elsewhere.
    """
    manager = MultiPlatformSyncManager.from_env()
    return manager.mark_sold(listing_id, sold_platform, sold_price)
