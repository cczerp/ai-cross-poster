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

        # Users table - for authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT 0,  -- Admin role flag
                is_active BOOLEAN DEFAULT 1,  -- Account active status
                notification_email TEXT,  -- Where to send sale notifications
                email_verified BOOLEAN DEFAULT 0,  -- Email verification status
                verification_token TEXT,  -- Token for email verification
                reset_token TEXT,  -- Token for password reset
                reset_token_expiry TIMESTAMP,  -- When reset token expires
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)

        # Marketplace credentials - per user
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marketplace_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,  -- 'poshmark', 'depop', 'varagesale', etc.
                username TEXT,
                password TEXT,  -- Encrypted or use secure storage in production
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, platform)
            )
        """)

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
                user_id INTEGER NOT NULL,  -- FK to users (owner of listing)
                collectible_id INTEGER,  -- FK to collectibles
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                cost REAL,  -- What you paid for it
                condition TEXT,
                category TEXT,
                item_type TEXT,  -- trading_card, clothing, electronics, collectible, general
                attributes TEXT,  -- JSON blob
                photos TEXT,  -- JSON array of photo paths
                quantity INTEGER DEFAULT 1,  -- Quantity available
                storage_location TEXT,  -- Physical location (B1, C2, etc.)
                sku TEXT,  -- Stock keeping unit / custom ID
                upc TEXT,  -- UPC / barcode
                status TEXT DEFAULT 'draft',  -- draft, active, sold, canceled
                sold_platform TEXT,  -- Which platform it sold on
                sold_date TIMESTAMP,
                sold_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collectible_id) REFERENCES collectibles(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
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
                status TEXT DEFAULT 'pending',  -- pending, active, sold, failed, canceled, pending_cancel
                posted_at TIMESTAMP,
                last_synced TIMESTAMP,
                cancel_scheduled_at TIMESTAMP,  -- When to auto-cancel (15 min cooldown)
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

        # Activity logs - track user actions for security and debugging
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,  -- login, logout, create_listing, delete_listing, etc.
                resource_type TEXT,  -- listing, user, credential, etc.
                resource_id INTEGER,
                details TEXT,  -- JSON blob with additional details
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
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

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id
            ON activity_logs(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_logs_action
            ON activity_logs(action)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_is_admin
            ON users(is_admin)
        """)

        # Run migrations
        self._run_migrations()

        self.conn.commit()

        # Run migrations for existing databases (must run before user_id index)
        self._run_migrations()

        # Create user_id index after migration (in case column didn't exist)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_listings_user_id
            ON listings(user_id)
        """)
        self.conn.commit()

    def _run_migrations(self):
        """Run database migrations for existing databases"""
        cursor = self.conn.cursor()

        # Migration: Add quantity and storage_location to listings table
        try:
            cursor.execute("SELECT quantity FROM listings LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            print("Running migration: Adding quantity column to listings table")
            cursor.execute("ALTER TABLE listings ADD COLUMN quantity INTEGER DEFAULT 1")
            self.conn.commit()

        try:
            cursor.execute("SELECT storage_location FROM listings LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            print("Running migration: Adding storage_location column to listings table")
            cursor.execute("ALTER TABLE listings ADD COLUMN storage_location TEXT")
            self.conn.commit()

        # Migration: Add cancel_scheduled_at to platform_listings table
        try:
            cursor.execute("SELECT cancel_scheduled_at FROM platform_listings LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            print("Running migration: Adding cancel_scheduled_at column to platform_listings table")
            cursor.execute("ALTER TABLE platform_listings ADD COLUMN cancel_scheduled_at TIMESTAMP")
            self.conn.commit()

        # Migration: Add user_id to listings table
        try:
            cursor.execute("SELECT user_id FROM listings LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            print("Running migration: Adding user_id column to listings table")
            # Add column with default value 1 (for existing listings, assume first user)
            cursor.execute("ALTER TABLE listings ADD COLUMN user_id INTEGER DEFAULT 1")
            self.conn.commit()
            # Create a default admin user if no users exist
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                print("Creating default user for existing listings")
                # Create default user with a secure random password (user should change this)
                import secrets
                default_password = secrets.token_urlsafe(16)
                from werkzeug.security import generate_password_hash
                cursor.execute("""
                    INSERT INTO users (id, username, email, password_hash)
                    VALUES (1, 'admin', 'admin@localhost', ?)
                """, (generate_password_hash(default_password),))
                self.conn.commit()
                print(f"Default user created: username='admin', password='{default_password}'")
                print("IMPORTANT: Please change this password after first login!")

        # Migration: Add notification_email to users table
        try:
            cursor.execute("SELECT notification_email FROM users LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            print("Running migration: Adding notification_email column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN notification_email TEXT")
            self.conn.commit()

        # Migration: Add admin and security columns to users table
        for col_name, col_def, default_msg in [
            ("is_admin", "BOOLEAN DEFAULT 0", "is_admin"),
            ("is_active", "BOOLEAN DEFAULT 1", "is_active"),
            ("email_verified", "BOOLEAN DEFAULT 0", "email_verified"),
            ("verification_token", "TEXT", "verification_token"),
            ("reset_token", "TEXT", "reset_token"),
            ("reset_token_expiry", "TIMESTAMP", "reset_token_expiry"),
        ]:
            try:
                cursor.execute(f"SELECT {col_name} FROM users LIMIT 1")
            except sqlite3.OperationalError:
                print(f"Running migration: Adding {default_msg} column to users table")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
                self.conn.commit()

        # Migration: Add SKU, UPC, and item_type to listings table
        for col_name, col_def, default_msg in [
            ("sku", "TEXT", "sku"),
            ("upc", "TEXT", "upc"),
            ("item_type", "TEXT", "item_type"),
        ]:
            try:
                cursor.execute(f"SELECT {col_name} FROM listings LIMIT 1")
            except sqlite3.OperationalError:
                print(f"Running migration: Adding {default_msg} column to listings table")
                cursor.execute(f"ALTER TABLE listings ADD COLUMN {col_name} {col_def}")
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
        user_id: int,
        collectible_id: Optional[int] = None,
        cost: Optional[float] = None,
        category: Optional[str] = None,
        item_type: Optional[str] = None,
        attributes: Optional[Dict] = None,
        quantity: int = 1,
        storage_location: Optional[str] = None,
        sku: Optional[str] = None,
        upc: Optional[str] = None,
    ) -> int:
        """Create a new listing"""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO listings (
                listing_uuid, user_id, collectible_id, title, description, price,
                cost, condition, category, item_type, attributes, photos, quantity,
                storage_location, sku, upc, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')
        """, (
            listing_uuid, user_id, collectible_id, title, description, price,
            cost, condition, category, item_type,
            json.dumps(attributes) if attributes else None,
            json.dumps(photos),
            quantity,
            storage_location,
            sku,
            upc,
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

    def get_drafts(self, limit: int = 100, user_id: Optional[int] = None) -> List[Dict]:
        """Get all draft listings, optionally filtered by user"""
        cursor = self.conn.cursor()
        if user_id is not None:
            cursor.execute("""
                SELECT * FROM listings
                WHERE status = 'draft' AND user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
        else:
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

    # ========================================================================
    # USER AUTHENTICATION METHODS
    # ========================================================================

    def create_user(self, username: str, email: str, password_hash: str) -> int:
        """Create a new user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        """, (username, email, password_hash))
        self.conn.commit()
        return cursor.lastrowid

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user_id,))
        self.conn.commit()

    def update_notification_email(self, user_id: int, notification_email: str):
        """Update user's notification email"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET notification_email = ?
            WHERE id = ?
        """, (notification_email, user_id))
        self.conn.commit()

    # ========================================================================
    # MARKETPLACE CREDENTIALS METHODS
    # ========================================================================

    def save_marketplace_credentials(self, user_id: int, platform: str, username: str, password: str):
        """Save or update marketplace credentials for a user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO marketplace_credentials
            (user_id, platform, username, password, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, platform, username, password))
        self.conn.commit()

    def get_marketplace_credentials(self, user_id: int, platform: str) -> Optional[Dict]:
        """Get marketplace credentials for a specific platform"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM marketplace_credentials
            WHERE user_id = ? AND platform = ?
        """, (user_id, platform))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_marketplace_credentials(self, user_id: int) -> List[Dict]:
        """Get all marketplace credentials for a user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM marketplace_credentials
            WHERE user_id = ?
            ORDER BY platform
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]

    def delete_marketplace_credentials(self, user_id: int, platform: str):
        """Delete marketplace credentials for a platform"""
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM marketplace_credentials
            WHERE user_id = ? AND platform = ?
        """, (user_id, platform))
        self.conn.commit()

    # ========================================================================
    # ACTIVITY LOG METHODS
    # ========================================================================

    def log_activity(
        self,
        action: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log a user activity"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO activity_logs (
                user_id, action, resource_type, resource_id, details,
                ip_address, user_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, action, resource_type, resource_id,
            json.dumps(details) if details else None,
            ip_address, user_agent
        ))
        self.conn.commit()

    def get_activity_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get activity logs with optional filters"""
        cursor = self.conn.cursor()
        sql = "SELECT * FROM activity_logs WHERE 1=1"
        params = []

        if user_id is not None:
            sql += " AND user_id = ?"
            params.append(user_id)

        if action:
            sql += " AND action = ?"
            params.append(action)

        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_user_activity_count(self, user_id: int) -> int:
        """Get total activity count for a user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM activity_logs WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchone()[0]

    # ========================================================================
    # ADMIN METHODS
    # ========================================================================

    def get_all_users(self, include_inactive: bool = False) -> List[Dict]:
        """Get all users (admin function)"""
        cursor = self.conn.cursor()
        if include_inactive:
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM users WHERE is_active = 1 ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def toggle_user_admin(self, user_id: int) -> bool:
        """Toggle admin status for a user"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False

        new_status = 0 if row[0] else 1
        cursor.execute("UPDATE users SET is_admin = ? WHERE id = ?", (new_status, user_id))
        self.conn.commit()
        return True

    def toggle_user_active(self, user_id: int) -> bool:
        """Toggle active status for a user"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_active FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False

        new_status = 0 if row[0] else 1
        cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
        self.conn.commit()
        return True

    def delete_user(self, user_id: int):
        """Delete a user and all their data (admin function)"""
        cursor = self.conn.cursor()

        # Delete user's marketplace credentials
        cursor.execute("DELETE FROM marketplace_credentials WHERE user_id = ?", (user_id,))

        # Delete user's listings
        cursor.execute("DELETE FROM listings WHERE user_id = ?", (user_id,))

        # Delete user's activity logs
        cursor.execute("DELETE FROM activity_logs WHERE user_id = ?", (user_id,))

        # Delete the user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))

        self.conn.commit()

    def get_system_stats(self) -> Dict:
        """Get system statistics (admin function)"""
        cursor = self.conn.cursor()

        stats = {}

        # User counts
        cursor.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        stats['admin_users'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        stats['active_users'] = cursor.fetchone()[0]

        # Listing counts
        cursor.execute("SELECT COUNT(*) FROM listings")
        stats['total_listings'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM listings WHERE status = 'draft'")
        stats['draft_listings'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM listings WHERE status = 'sold'")
        stats['sold_listings'] = cursor.fetchone()[0]

        # Activity count
        cursor.execute("SELECT COUNT(*) FROM activity_logs WHERE created_at > datetime('now', '-7 days')")
        stats['activity_last_7_days'] = cursor.fetchone()[0]

        return stats

    # ========================================================================
    # EMAIL TOKEN METHODS
    # ========================================================================

    def set_verification_token(self, user_id: int, token: str):
        """Set email verification token"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET verification_token = ?
            WHERE id = ?
        """, (token, user_id))
        self.conn.commit()

    def verify_email(self, token: str) -> bool:
        """Verify email with token"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET email_verified = 1, verification_token = NULL
            WHERE verification_token = ?
        """, (token,))
        self.conn.commit()
        return cursor.rowcount > 0

    def set_reset_token(self, user_id: int, token: str, expiry_hours: int = 24):
        """Set password reset token"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET reset_token = ?,
                reset_token_expiry = datetime('now', '+' || ? || ' hours')
            WHERE id = ?
        """, (token, expiry_hours, user_id))
        self.conn.commit()

    def verify_reset_token(self, token: str) -> Optional[Dict]:
        """Verify reset token and return user if valid"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM users
            WHERE reset_token = ?
            AND reset_token_expiry > datetime('now')
        """, (token,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_password(self, user_id: int, new_password_hash: str):
        """Update user password and clear reset token"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET password_hash = ?,
                reset_token = NULL,
                reset_token_expiry = NULL
            WHERE id = ?
        """, (new_password_hash, user_id))
        self.conn.commit()

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
