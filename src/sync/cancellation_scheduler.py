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

        # TODO: Call platform API to cancel the listing
        # For now, we'll just mark it as canceled in the database

        try:
            # Example API calls (to be implemented):
            # if platform == 'ebay':
            #     self.cancel_on_ebay(platform_listing_id)
            # elif platform == 'mercari':
            #     self.cancel_on_mercari(platform_listing_id)

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
