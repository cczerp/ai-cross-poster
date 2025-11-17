"""
Database Schema for AI Cross-Poster
====================================
SQLite database for collectibles, listings, and sync tracking.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json


class Database:
    """Main database handler for AI Cross-Poster"""

    def __init__(self, db_path: str = "./data/cross_poster.db"):
        """Initialize database connection"""
        self.db_path = db_path

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Create tables
        self._create_tables()

    def _create_tables(self):
        """Create all database tables"""
        cursor = self.conn.cursor()

        # Collectibles database table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collectibles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                brand TEXT,
                model TEXT,
                year INTEGER,
                condition TEXT,
                estimated_value_low REAL,
                estimated_value_high REAL,
                estimated_value_avg REAL,
                market_data TEXT,  -- JSON blob with pricing history
                attributes TEXT,   -- JSON blob with item attributes
                image_urls TEXT,   -- JSON array of image URLs
                identified_by TEXT,  -- 'claude', 'gpt4', 'manual'
                confidence_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                times_found INTEGER DEFAULT 1,
                notes TEXT
            )
        """)

        # Listings table - tracks all your listings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_uuid TEXT UNIQUE NOT NULL,  -- Internal unique ID
                collectible_id INTEGER,  -- FK to collectibles
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                cost REAL,  -- What you paid for it
                condition TEXT,
                category TEXT,
                attributes TEXT,  -- JSON blob
                photos TEXT,  -- JSON array of photo paths
                status TEXT DEFAULT 'draft',  -- draft, active, sold, canceled
                sold_platform TEXT,  -- Which platform it sold on
                sold_date TIMESTAMP,
                sold_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collectible_id) REFERENCES collectibles(id)
            )
        """)

        # Platform listings - track where each listing is posted
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS platform_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER NOT NULL,
                platform TEXT NOT NULL,  -- ebay, mercari, facebook, poshmark
                platform_listing_id TEXT,  -- ID from the platform
                platform_url TEXT,
                status TEXT DEFAULT 'pending',  -- pending, active, sold, failed, canceled
                posted_at TIMESTAMP,
                last_synced TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (listing_id) REFERENCES listings(id),
                UNIQUE(listing_id, platform)
            )
        """)

        # Sync log - track all sync operations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                action TEXT NOT NULL,  -- create, update, cancel, check_status
                status TEXT,  -- success, failed
                details TEXT,  -- JSON blob with details
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (listing_id) REFERENCES listings(id)
            )
        """)

        # Notifications/alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,  -- sale, offer, listing_failed, price_alert
                listing_id INTEGER,
                platform TEXT,
                title TEXT NOT NULL,
                message TEXT,
                data TEXT,  -- JSON blob with notification data
                is_read BOOLEAN DEFAULT 0,
                sent_email BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (listing_id) REFERENCES listings(id)
            )
        """)

        # Price alerts - track collectibles you're watching
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collectible_id INTEGER NOT NULL,
                target_price REAL NOT NULL,
                condition TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collectible_id) REFERENCES collectibles(id)
            )
        """)

        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_listings_uuid
            ON listings(listing_uuid)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_listings_status
            ON listings(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_platform_listings_status
            ON platform_listings(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_collectibles_name
            ON collectibles(name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_unread
            ON notifications(is_read)
        """)

        # Run migrations
        self._run_migrations()

        self.conn.commit()

    def _run_migrations(self):
        """Run database migrations for schema updates"""
        cursor = self.conn.cursor()

        # Migration: Add storage_location column to listings table
        try:
            cursor.execute("SELECT storage_location FROM listings LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            cursor.execute("ALTER TABLE listings ADD COLUMN storage_location TEXT")
            self.conn.commit()

    # ========================================================================
    # COLLECTIBLES METHODS
    # ========================================================================

    def add_collectible(
        self,
        name: str,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        condition: Optional[str] = None,
        estimated_value_low: Optional[float] = None,
        estimated_value_high: Optional[float] = None,
        market_data: Optional[Dict] = None,
        attributes: Optional[Dict] = None,
        image_urls: Optional[List[str]] = None,
        identified_by: str = "claude",
        confidence_score: float = 0.0,
        notes: Optional[str] = None,
    ) -> int:
        """Add a collectible to the database"""
        cursor = self.conn.cursor()

        # Calculate average value
        avg_value = None
        if estimated_value_low and estimated_value_high:
            avg_value = (estimated_value_low + estimated_value_high) / 2

        cursor.execute("""
            INSERT INTO collectibles (
                name, category, brand, model, year, condition,
                estimated_value_low, estimated_value_high, estimated_value_avg,
                market_data, attributes, image_urls,
                identified_by, confidence_score, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, category, brand, model, year, condition,
            estimated_value_low, estimated_value_high, avg_value,
            json.dumps(market_data) if market_data else None,
            json.dumps(attributes) if attributes else None,
            json.dumps(image_urls) if image_urls else None,
            identified_by, confidence_score, notes
        ))

        self.conn.commit()
        return cursor.lastrowid

    def find_collectible(self, name: str, brand: Optional[str] = None) -> Optional[Dict]:
        """Find a collectible by name and optional brand"""
        cursor = self.conn.cursor()

        if brand:
            cursor.execute("""
                SELECT * FROM collectibles
                WHERE name LIKE ? AND brand LIKE ?
                ORDER BY times_found DESC, confidence_score DESC
                LIMIT 1
            """, (f"%{name}%", f"%{brand}%"))
        else:
            cursor.execute("""
                SELECT * FROM collectibles
                WHERE name LIKE ?
                ORDER BY times_found DESC, confidence_score DESC
                LIMIT 1
            """, (f"%{name}%",))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def increment_collectible_found(self, collectible_id: int):
        """Increment the times_found counter for a collectible"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE collectibles
            SET times_found = times_found + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (collectible_id,))
        self.conn.commit()

    def search_collectibles(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> List[Dict]:
        """Search collectibles database"""
        cursor = self.conn.cursor()

        sql = "SELECT * FROM collectibles WHERE 1=1"
        params = []

        if query:
            sql += " AND (name LIKE ? OR brand LIKE ? OR model LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])

        if category:
            sql += " AND category LIKE ?"
            params.append(f"%{category}%")

        if brand:
            sql += " AND brand LIKE ?"
            params.append(f"%{brand}%")

        if min_value:
            sql += " AND estimated_value_avg >= ?"
            params.append(min_value)

        if max_value:
            sql += " AND estimated_value_avg <= ?"
            params.append(max_value)

        sql += " ORDER BY times_found DESC, confidence_score DESC"

        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    # ========================================================================
    # LISTINGS METHODS
    # ========================================================================

    def create_listing(
        self,
        listing_uuid: str,
        title: str,
        description: str,
        price: float,
        condition: str,
        photos: List[str],
        collectible_id: Optional[int] = None,
        cost: Optional[float] = None,
        category: Optional[str] = None,
        attributes: Optional[Dict] = None,
        storage_location: Optional[str] = None,
    ) -> int:
        """Create a new listing"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO listings (
                listing_uuid, collectible_id, title, description, price,
                cost, condition, category, attributes, photos, status, storage_location
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?)
        """, (
            listing_uuid, collectible_id, title, description, price,
            cost, condition, category,
            json.dumps(attributes) if attributes else None,
            json.dumps(photos),
            storage_location,
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_listing(self, listing_id: int) -> Optional[Dict]:
        """Get a listing by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_listing_by_uuid(self, listing_uuid: str) -> Optional[Dict]:
        """Get a listing by UUID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM listings WHERE listing_uuid = ?", (listing_uuid,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_drafts(self, limit: int = 100) -> List[Dict]:
        """Get all draft listings"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM listings
            WHERE status = 'draft'
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def update_listing_status(self, listing_id: int, status: str):
        """Update listing status"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE listings
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, listing_id))
        self.conn.commit()

    def delete_listing(self, listing_id: int):
        """Delete a listing and its platform listings"""
        cursor = self.conn.cursor()
        # Delete platform listings first
        cursor.execute("DELETE FROM platform_listings WHERE listing_id = ?", (listing_id,))
        # Delete listing
        cursor.execute("DELETE FROM listings WHERE id = ?", (listing_id,))
        self.conn.commit()

    def mark_listing_sold(
        self,
        listing_id: int,
        platform: str,
        sold_price: Optional[float] = None
    ):
        """Mark a listing as sold"""
        cursor = self.conn.cursor()

        # Update main listing
        cursor.execute("""
            UPDATE listings
            SET status = 'sold',
                sold_platform = ?,
                sold_date = CURRENT_TIMESTAMP,
                sold_price = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (platform, sold_price, listing_id))

        # Update all platform listings to canceled (except the one that sold)
        cursor.execute("""
            UPDATE platform_listings
            SET status = CASE
                WHEN platform = ? THEN 'sold'
                ELSE 'canceled'
            END,
            last_synced = CURRENT_TIMESTAMP
            WHERE listing_id = ?
        """, (platform, listing_id))

        self.conn.commit()

    # ========================================================================
    # PLATFORM LISTINGS METHODS
    # ========================================================================

    def add_platform_listing(
        self,
        listing_id: int,
        platform: str,
        platform_listing_id: Optional[str] = None,
        platform_url: Optional[str] = None,
        status: str = "pending",
    ) -> int:
        """Add a platform listing"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO platform_listings (
                listing_id, platform, platform_listing_id,
                platform_url, status, posted_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (listing_id, platform, platform_listing_id, platform_url, status))

        self.conn.commit()
        return cursor.lastrowid

    def update_platform_listing_status(
        self,
        listing_id: int,
        platform: str,
        status: str,
        platform_listing_id: Optional[str] = None,
        platform_url: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Update platform listing status"""
        cursor = self.conn.cursor()

        cursor.execute("""
            UPDATE platform_listings
            SET status = ?,
                platform_listing_id = COALESCE(?, platform_listing_id),
                platform_url = COALESCE(?, platform_url),
                error_message = ?,
                last_synced = CURRENT_TIMESTAMP
            WHERE listing_id = ? AND platform = ?
        """, (status, platform_listing_id, platform_url, error_message, listing_id, platform))

        self.conn.commit()

    def get_platform_listings(self, listing_id: int) -> List[Dict]:
        """Get all platform listings for a listing"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM platform_listings WHERE listing_id = ?
        """, (listing_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_active_listings_by_platform(self, platform: str) -> List[Dict]:
        """Get all active listings for a specific platform"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT l.*, pl.platform_listing_id, pl.platform_url, pl.status as platform_status
            FROM listings l
            JOIN platform_listings pl ON l.id = pl.listing_id
            WHERE pl.platform = ? AND pl.status = 'active'
        """, (platform,))
        return [dict(row) for row in cursor.fetchall()]

    # ========================================================================
    # SYNC LOG METHODS
    # ========================================================================

    def log_sync(
        self,
        listing_id: int,
        platform: str,
        action: str,
        status: str,
        details: Optional[Dict] = None,
    ):
        """Log a sync operation"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sync_log (listing_id, platform, action, status, details)
            VALUES (?, ?, ?, ?, ?)
        """, (listing_id, platform, action, status, json.dumps(details) if details else None))
        self.conn.commit()

    # ========================================================================
    # NOTIFICATIONS METHODS
    # ========================================================================

    def create_notification(
        self,
        type: str,
        title: str,
        message: str,
        listing_id: Optional[int] = None,
        platform: Optional[str] = None,
        data: Optional[Dict] = None,
    ) -> int:
        """Create a notification"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO notifications (
                type, listing_id, platform, title, message, data
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (type, listing_id, platform, title, message, json.dumps(data) if data else None))
        self.conn.commit()
        return cursor.lastrowid

    def get_unread_notifications(self) -> List[Dict]:
        """Get all unread notifications"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM notifications
            WHERE is_read = 0
            ORDER BY created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def mark_notification_read(self, notification_id: int):
        """Mark a notification as read"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE notifications
            SET is_read = 1
            WHERE id = ?
        """, (notification_id,))
        self.conn.commit()

    def mark_notification_emailed(self, notification_id: int):
        """Mark a notification as emailed"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE notifications
            SET sent_email = 1
            WHERE id = ?
        """, (notification_id,))
        self.conn.commit()

    # ========================================================================
    # PRICE ALERTS METHODS
    # ========================================================================

    def add_price_alert(
        self,
        collectible_id: int,
        target_price: float,
        condition: Optional[str] = None,
    ) -> int:
        """Add a price alert for a collectible"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO price_alerts (collectible_id, target_price, condition)
            VALUES (?, ?, ?)
        """, (collectible_id, target_price, condition))
        self.conn.commit()
        return cursor.lastrowid

    def get_active_price_alerts(self) -> List[Dict]:
        """Get all active price alerts"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT pa.*, c.name as collectible_name, c.brand, c.estimated_value_avg
            FROM price_alerts pa
            JOIN collectibles c ON pa.collectible_id = c.id
            WHERE pa.is_active = 1
        """)
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


# Singleton instance
_db_instance = None

def get_db() -> Database:
    """Get database singleton instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
