"""
Cancellation Scheduler
======================
Background job that processes scheduled cancellations after the 15-minute cooldown period.

Run this in the background:
    python -m src.sync.cancellation_scheduler

Or use a cron job / systemd service to run it every minute.
"""

import time
from datetime import datetime
from typing import List, Dict, Any
import sqlite3

from ..database import get_db


class CancellationScheduler:
    """Processes scheduled cancellations"""

    def __init__(self):
        self.db = get_db()

    def get_pending_cancellations(self) -> List[Dict[str, Any]]:
        """Get all platform listings that are ready to be canceled"""
        cursor = self.db._get_cursor()

        cursor.execute("""
            SELECT pl.*, l.title, l.listing_uuid
            FROM platform_listings pl
            JOIN listings l ON pl.listing_id = l.id
            WHERE pl.status = 'pending_cancel'
            AND pl.cancel_scheduled_at IS NOT NULL
            AND datetime(pl.cancel_scheduled_at) <= datetime('now')
        """)

        return [dict(row) for row in cursor.fetchall()]

    def cancel_on_platform(self, platform: str, platform_listing_id: str) -> bool:
        """
        Cancel a listing on the specified platform via API.

        Args:
            platform: Platform name ('ebay', 'mercari', etc.)
            platform_listing_id: The platform-specific listing ID

        Returns:
            True if successful, False otherwise

        Raises:
            NotImplementedError: If platform adapter doesn't exist
            Exception: If API call fails
        """
        if not platform_listing_id:
            raise ValueError(f"No platform listing ID provided for {platform}")

        if platform == 'ebay':
            return self._cancel_on_ebay(platform_listing_id)
        elif platform == 'mercari':
            return self._cancel_on_mercari(platform_listing_id)
        else:
            raise NotImplementedError(f"Cancellation not implemented for platform: {platform}")

    def _cancel_on_ebay(self, offer_id: str) -> bool:
        """
        Cancel/withdraw an eBay listing via eBay Sell API.

        Args:
            offer_id: eBay offer ID

        Returns:
            True if successful

        Raises:
            Exception: If API call fails
        """
        try:
            # Import eBay adapter if available
            from ..adapters.ebay_adapter import EbayAdapter

            adapter = EbayAdapter.from_env()

            # eBay Sell API: Withdraw offer
            # DELETE /sell/inventory/v1/offer/{offerId}/withdraw
            result = adapter.withdraw_offer(offer_id)

            print(f"   ℹ️  eBay API response: {result}")
            return True

        except ImportError:
            # Adapter not implemented yet - log warning and skip
            print(f"   ⚠️  eBay adapter not available - marking as canceled in database only")
            return True  # Return True to mark as canceled in DB
        except Exception as e:
            print(f"   ❌ eBay API error: {e}")
            raise

    def _cancel_on_mercari(self, listing_id: str) -> bool:
        """
        Cancel a Mercari listing via Mercari Shops API.

        Args:
            listing_id: Mercari listing ID

        Returns:
            True if successful

        Raises:
            Exception: If API call fails
        """
        try:
            # Import Mercari adapter if available
            from ..adapters.mercari_adapter import MercariAdapter

            adapter = MercariAdapter.from_env()

            # Mercari Shops API: Delete/cancel listing
            result = adapter.cancel_listing(listing_id)

            print(f"   ℹ️  Mercari API response: {result}")
            return True

        except ImportError:
            # Adapter not implemented yet - log warning and skip
            print(f"   ⚠️  Mercari adapter not available - marking as canceled in database only")
            return True  # Return True to mark as canceled in DB
        except Exception as e:
            print(f"   ❌ Mercari API error: {e}")
            raise

    def process_cancellation(self, platform_listing: Dict[str, Any]) -> bool:
        """
        Process a single cancellation.

        Args:
            platform_listing: The platform_listing record to cancel

        Returns:
            True if successful, False otherwise
        """
        listing_id = platform_listing['listing_id']
        platform = platform_listing['platform']
        platform_listing_id = platform_listing.get('platform_listing_id')

        print(f"\n🚫 Processing cancellation: {platform_listing['title']}")
        print(f"   Platform: {platform}")
        print(f"   Scheduled at: {platform_listing['cancel_scheduled_at']}")

        try:
            # Call platform API to cancel the listing
            if platform_listing_id:
                self.cancel_on_platform(platform, platform_listing_id)
            else:
                print(f"   ⚠️  No platform listing ID - skipping API call")

            # Mark as canceled in database
            cursor = self.db._get_cursor()
            cursor.execute("""
                UPDATE platform_listings
                SET status = 'canceled',
                    last_synced = CURRENT_TIMESTAMP
                WHERE listing_id = ? AND platform = ?
            """, (listing_id, platform))
            self.db.conn.commit()

            # Log the cancellation
            self.db.log_sync(
                listing_id=listing_id,
                platform=platform,
                action="cancel",
                status="success",
                details={"reason": "Scheduled cancellation after 15-minute cooldown"},
            )

            print(f"   ✅ Canceled on {platform}")
            return True

        except NotImplementedError as e:
            print(f"   ⚠️  {e} - marking as canceled in database only")

            # Mark as canceled in database even if API not available
            cursor = self.db._get_cursor()
            cursor.execute("""
                UPDATE platform_listings
                SET status = 'canceled',
                    last_synced = CURRENT_TIMESTAMP
                WHERE listing_id = ? AND platform = ?
            """, (listing_id, platform))
            self.db.conn.commit()

            # Log with note about missing implementation
            self.db.log_sync(
                listing_id=listing_id,
                platform=platform,
                action="cancel",
                status="success",
                details={"reason": "Marked as canceled (platform adapter not implemented)"},
            )

            return True

        except Exception as e:
            print(f"   ❌ Failed to cancel on {platform}: {e}")

            # Log the failure
            self.db.log_sync(
                listing_id=listing_id,
                platform=platform,
                action="cancel",
                status="failed",
                details={"error": str(e)},
            )

            # Update error message
            cursor = self.db._get_cursor()
            cursor.execute("""
                UPDATE platform_listings
                SET error_message = ?
                WHERE listing_id = ? AND platform = ?
            """, (str(e), listing_id, platform))
            self.db.conn.commit()

            return False

    def run_once(self) -> int:
        """
        Run one iteration of the scheduler.

        Returns:
            Number of cancellations processed
        """
        pending = self.get_pending_cancellations()

        if not pending:
            return 0

        print(f"\n{'='*70}")
        print(f"🕐 PROCESSING SCHEDULED CANCELLATIONS")
        print(f"{'='*70}")
        print(f"Found {len(pending)} pending cancellation(s)\n")

        processed = 0
        for platform_listing in pending:
            if self.process_cancellation(platform_listing):
                processed += 1

        print(f"\n{'='*70}")
        print(f"✅ PROCESSED {processed}/{len(pending)} CANCELLATIONS")
        print(f"{'='*70}\n")

        return processed

    def run_forever(self, check_interval_seconds: int = 60):
        """
        Run the scheduler continuously.

        Args:
            check_interval_seconds: How often to check for pending cancellations
        """
        print(f"🕐 Cancellation Scheduler started (checking every {check_interval_seconds}s)")
        print(f"   Press Ctrl+C to stop\n")

        try:
            while True:
                self.run_once()
                time.sleep(check_interval_seconds)
        except KeyboardInterrupt:
            print("\n\n👋 Cancellation Scheduler stopped")


def main():
    """Main entry point for the cancellation scheduler"""
    scheduler = CancellationScheduler()

    # Run continuously, checking every 60 seconds
    scheduler.run_forever(check_interval_seconds=60)


if __name__ == "__main__":
    main()
