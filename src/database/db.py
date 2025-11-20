"""
Database Schema for AI Cross-Poster
====================================
Supports both SQLite (local dev) and PostgreSQL (production).
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json


class Database:
    """Main database handler for AI Cross-Poster"""

    def __init__(self, db_path: str = "./data/cross_poster.db"):
        """Initialize database connection"""
        self.db_path = db_path

        # Check for PostgreSQL DATABASE_URL
        database_url = os.getenv('DATABASE_URL')

        if database_url:
            # Use PostgreSQL
            print("🐘 Connecting to PostgreSQL database...")
            import psycopg2
            import psycopg2.extras

            self.is_postgres = True
            self.conn = psycopg2.connect(database_url)
            # Use RealDictCursor for dict-like row access
            self.cursor_factory = psycopg2.extras.RealDictCursor
        else:
            # Use SQLite
            print("📁 Using SQLite database...")
            import sqlite3

            self.is_postgres = False

            # Ensure data directory exists
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

            # Initialize connection
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row

        # Create tables
        self._create_tables()

    def _get_cursor(self):
        """Get appropriate cursor for database type with auto-converting execute"""
        if self.is_postgres:
            cursor = self.conn.cursor(cursor_factory=self.cursor_factory)
        else:
            cursor = self.conn.cursor()

        # Wrap execute to auto-convert SQL and handle RETURNING for lastrowid
        original_execute = cursor.execute
        cursor._last_insert_id = None

        def converting_execute(sql, params=None):
            converted_sql = sql.replace('?', '%s') if self.is_postgres else sql

            # For PostgreSQL INSERT statements, add RETURNING id if not present
            if self.is_postgres and 'INSERT' in converted_sql.upper() and 'RETURNING' not in converted_sql.upper():
                converted_sql = converted_sql.rstrip().rstrip(';') + ' RETURNING id'

            if params:
                result = original_execute(converted_sql, params)
            else:
                result = original_execute(converted_sql)

            # Fetch the RETURNING id for PostgreSQL
            if self.is_postgres and 'RETURNING' in converted_sql.upper():
                try:
                    row = cursor.fetchone()
                    if row:
                        cursor._last_insert_id = row.get('id') if isinstance(row, dict) else row[0]
                except:
                    pass

            return result

        cursor.execute = converting_execute

        # Add lastrowid property for PostgreSQL compatibility
        if self.is_postgres:
            cursor.__class__.lastrowid = property(lambda self: self._last_insert_id or 0)

        return cursor

    def _sql(self, sqlite_sql: str, postgres_sql: Optional[str] = None) -> str:
        """Return appropriate SQL for database type"""
        if self.is_postgres and postgres_sql:
            return postgres_sql
        elif self.is_postgres:
            # Auto-convert common SQLite -> PostgreSQL patterns
            sql = sqlite_sql
            sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            sql = sql.replace('BOOLEAN DEFAULT 0', 'BOOLEAN DEFAULT FALSE')
            sql = sql.replace('BOOLEAN DEFAULT 1', 'BOOLEAN DEFAULT TRUE')
            # Convert ? placeholders to %s for PostgreSQL
            sql = sql.replace('?', '%s')
            return sql
        else:
            return sqlite_sql

    def _execute(self, cursor, sql: str, params=None):
        """Execute SQL with automatic conversion for PostgreSQL"""
        converted_sql = self._sql(sql)
        if params:
            cursor.execute(converted_sql, params)
        else:
            cursor.execute(converted_sql)
        return cursor

    def _create_tables(self):
        """Create all database tables"""
        cursor = self._get_cursor()

        # Users table - for authentication
        cursor.execute(self._sql("""
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
        """))

        # Marketplace credentials - per user
        cursor.execute(self._sql("""
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
        """))

        # Collectibles database table
        cursor.execute(self._sql("""
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
        """))

        # Listings table - tracks all your listings
        cursor.execute(self._sql("""
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
        """))

        # Training data table - Knowledge Distillation (baby bird learns from Claude)
        # MUST be created AFTER listings table due to FK constraint
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                listing_id INTEGER,
                collectible_id INTEGER,
                photo_paths TEXT,  -- JSON array of photo paths
                input_data TEXT,  -- JSON: Gemini's basic analysis (student sees this)
                teacher_output TEXT,  -- JSON: Claude's deep analysis (student learns from this)
                student_output TEXT,  -- JSON: Student model's attempt (once trained)
                student_confidence REAL,  -- How confident was student?
                used_teacher BOOLEAN DEFAULT 1,  -- Did we use Claude or student?
                quality_score REAL,  -- Human feedback on quality (optional)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (listing_id) REFERENCES listings(id),
                FOREIGN KEY (collectible_id) REFERENCES collectibles(id)
            )
        """))

        # Create index for faster training data queries
        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_training_data_created
            ON training_data(created_at DESC)
        """))

        # Platform listings - track where each listing is posted
        cursor.execute(self._sql("""
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
        """))

        # Sync log - track all sync operations
        cursor.execute(self._sql("""
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
        """))

        # Platform activity - monitor external platforms for sold items & messages
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS platform_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,  -- ebay, mercari, etc.
                activity_type TEXT NOT NULL,  -- 'sold', 'message', 'offer', 'view', 'favorite'
                platform_listing_id TEXT,  -- ID of the listing on that platform
                listing_id INTEGER,  -- FK to our listings table (if matched)
                title TEXT,  -- Title of the item
                buyer_username TEXT,  -- Username of buyer (if applicable)
                message_text TEXT,  -- Message content (for 'message' type)
                sold_price REAL,  -- Sale price (for 'sold' type)
                activity_date TIMESTAMP,  -- When the activity occurred
                is_read BOOLEAN DEFAULT 0,  -- Has user acknowledged this?
                is_synced_to_inventory BOOLEAN DEFAULT 0,  -- Has sold item been marked in our system?
                raw_data TEXT,  -- JSON: Full data from platform API/scrape
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (listing_id) REFERENCES listings(id)
            )
        """))

        # Create index for faster activity queries
        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_platform_activity_user_unread
            ON platform_activity(user_id, is_read, created_at DESC)
        """))

        # ========================================
        # STORAGE SYSTEM (Standalone Organization Tool)
        # ========================================

        # Storage bins - for physical organization (clothing, cards, etc.)
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS storage_bins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bin_name TEXT NOT NULL,  -- 'A', 'B', 'C' or custom name
                bin_type TEXT NOT NULL,  -- 'clothing', 'cards'
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, bin_name, bin_type)
            )
        """))

        # Storage sections - compartments within bins
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS storage_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bin_id INTEGER NOT NULL,
                section_name TEXT NOT NULL,  -- 'A1', 'A2', 'A3' or '1', '2', '3'
                capacity INTEGER,  -- Max items (optional)
                item_count INTEGER DEFAULT 0,  -- Current items
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bin_id) REFERENCES storage_bins(id),
                UNIQUE(bin_id, section_name)
            )
        """))

        # Storage items - physical items in storage (NOT listings)
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS storage_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                storage_id TEXT UNIQUE NOT NULL,  -- A2-14, FB-A1-12, etc.
                bin_id INTEGER NOT NULL,
                section_id INTEGER,
                item_type TEXT,  -- 'clothing', 'shoes', 'accessories', 'card', 'collectible'
                category TEXT,  -- For cards: 'FB' (Football), 'PKMN' (Pokemon), etc.
                title TEXT,
                description TEXT,
                quantity INTEGER DEFAULT 1,
                photos TEXT,  -- JSON array of photo paths
                notes TEXT,
                listing_id INTEGER,  -- Optional link to listing (if user lists it later)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (bin_id) REFERENCES storage_bins(id),
                FOREIGN KEY (section_id) REFERENCES storage_sections(id),
                FOREIGN KEY (listing_id) REFERENCES listings(id)
            )
        """))

        # Create indexes for faster storage queries
        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_storage_items_user
            ON storage_items(user_id, created_at DESC)
        """))

        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_storage_items_bin_section
            ON storage_items(bin_id, section_id)
        """))

        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_storage_items_storage_id
            ON storage_items(storage_id)
        """))

        # ========================================
        # CARD COLLECTION SYSTEM (Standalone Collection Manager)
        # ========================================

        # Card collections - unified card data for all card types
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS card_collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,

                -- Universal Fields (all cards)
                card_uuid TEXT UNIQUE NOT NULL,  -- Internal unique ID
                card_type TEXT NOT NULL,  -- 'pokemon', 'mtg', 'yugioh', 'sports_nfl', 'sports_nba', 'sports_mlb', etc.
                title TEXT NOT NULL,  -- Full card name/title
                card_number TEXT,  -- Card number in set
                quantity INTEGER DEFAULT 1,

                -- Organization Fields
                organization_mode TEXT,  -- Current organization: 'by_set', 'by_year', 'by_sport', 'by_brand', 'by_game', 'by_rarity', 'by_number', 'by_grading', 'by_value', 'by_binder', 'custom'
                primary_category TEXT,  -- Auto-assigned based on organization mode
                custom_categories TEXT,  -- JSON array of custom tags

                -- Physical Location (optional link to storage)
                storage_location TEXT,  -- Free-form location (Binder A Page 1, Box 3, etc.)
                storage_item_id INTEGER,  -- Optional FK to storage_items

                -- TCG Fields (Pokémon, MTG, Yu-Gi-Oh, etc.)
                game_name TEXT,  -- 'Pokemon', 'Magic: The Gathering', 'Yu-Gi-Oh!', etc.
                set_name TEXT,  -- Set name
                set_code TEXT,  -- Set abbreviation/code
                set_symbol TEXT,  -- Set symbol description
                rarity TEXT,  -- Common, Uncommon, Rare, Ultra Rare, Secret Rare, etc.
                card_subtype TEXT,  -- Trainer, Energy, Creature Type, Spell Type, etc.
                format_legality TEXT,  -- JSON: Standard, Expanded, Legacy, Modern, Vintage, etc.

                -- Sports Card Fields (NFL, NBA, MLB, etc.)
                sport TEXT,  -- 'NFL', 'NBA', 'MLB', 'NHL', etc.
                year INTEGER,  -- Card year
                brand TEXT,  -- Topps, Panini, Upper Deck, etc.
                series TEXT,  -- Series/product line
                player_name TEXT,  -- Player name (for sports cards)
                team TEXT,  -- Team name
                is_rookie_card BOOLEAN DEFAULT 0,  -- RC flag
                parallel_color TEXT,  -- Parallel/variant color
                insert_series TEXT,  -- Insert/special series

                -- Grading & Value
                grading_company TEXT,  -- PSA, BGS, CGC, etc.
                grading_score REAL,  -- 9.5, 10, etc.
                grading_serial TEXT,  -- Grading serial number
                estimated_value REAL,  -- Current estimated value (optional)
                value_tier TEXT,  -- 'under_10', '10_50', '50_100', '100_500', 'over_500'
                purchase_price REAL,  -- What you paid (optional)

                -- Photos & Notes
                photos TEXT,  -- JSON array of photo paths
                notes TEXT,  -- User notes

                -- Metadata
                ai_identified BOOLEAN DEFAULT 0,  -- Was this auto-identified by AI?
                ai_confidence REAL,  -- Confidence score
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (storage_item_id) REFERENCES storage_items(id)
            )
        """))

        # Organization presets - saved organization modes per user
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS card_organization_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                preset_name TEXT NOT NULL,  -- 'My Pokemon Sets', 'NFL by Year', etc.
                card_type_filter TEXT,  -- Filter by card type (optional)
                organization_mode TEXT NOT NULL,  -- 'by_set', 'by_year', etc.
                sort_order TEXT,  -- 'asc' or 'desc'
                filters TEXT,  -- JSON: Additional filters
                is_active BOOLEAN DEFAULT 0,  -- Currently active preset
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, preset_name)
            )
        """))

        # Custom categories - user-defined categories/tags
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS card_custom_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category_name TEXT NOT NULL,  -- 'Trade', 'Keep', 'Sell', 'Duplicates', etc.
                category_color TEXT,  -- Hex color for UI
                category_icon TEXT,  -- Icon name
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, category_name)
            )
        """))

        # Card collection indexes
        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_card_collections_user
            ON card_collections(user_id, created_at DESC)
        """))

        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_card_collections_type
            ON card_collections(card_type)
        """))

        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_card_collections_org_mode
            ON card_collections(organization_mode, primary_category)
        """))

        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_card_collections_set
            ON card_collections(set_code, card_number)
        """))

        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_card_collections_sport_year
            ON card_collections(sport, year, brand)
        """))

        # Notifications/alerts table
        cursor.execute(self._sql("""
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
        """))

        # Price alerts - track collectibles you're watching
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collectible_id INTEGER NOT NULL,
                target_price REAL NOT NULL,
                condition TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collectible_id) REFERENCES collectibles(id)
            )
        """))

        # Activity logs - track user actions for security and debugging
        cursor.execute(self._sql("""
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
        """))

        # Create indexes for better performance
        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_listings_uuid
            ON listings(listing_uuid)
        """))

        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_listings_status
            ON listings(status)
        """))

        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_platform_listings_status
            ON platform_listings(status)
        """))

        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_collectibles_name
            ON collectibles(name)
        """))

        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_notifications_unread
            ON notifications(is_read)
        """))

        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id
            ON activity_logs(user_id)
        """))

        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_activity_logs_action
            ON activity_logs(action)
        """))

        # Run migrations BEFORE creating indexes on migrated columns
        self._run_migrations()

        # Create indexes on migrated columns (after migrations complete)
        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_users_is_admin
            ON users(is_admin)
        """))

        # Create user_id index after migration (in case column didn't exist)
        cursor.execute(self._sql("""
            CREATE INDEX IF NOT EXISTS idx_listings_user_id
            ON listings(user_id)
        """))

        self.conn.commit()

    def _run_migrations(self):
        """Run database migrations for existing databases"""
        # PostgreSQL creates fresh tables with latest schema, no migrations needed
        if self.is_postgres:
            print("📊 PostgreSQL: Using latest schema (no migrations needed)")
            return

        cursor = self._get_cursor()
        import sqlite3

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

        # Migration: Add deep_analysis and embedding to collectibles table (for RAG)
        for col_name, col_def, default_msg in [
            ("deep_analysis", "TEXT", "deep_analysis (Claude analysis JSON)"),
            ("embedding", "TEXT", "embedding (vector for similarity search)"),
            ("franchise", "TEXT", "franchise (Pokemon, Star Wars, etc.)"),
            ("rarity_level", "TEXT", "rarity_level (Common, Rare, Ultra Rare)"),
        ]:
            try:
                cursor.execute(f"SELECT {col_name} FROM collectibles LIMIT 1")
            except sqlite3.OperationalError:
                print(f"Running migration: Adding {default_msg} column to collectibles table")
                cursor.execute(f"ALTER TABLE collectibles ADD COLUMN {col_name} {col_def}")
                self.conn.commit()

        # Migration: Add platform_statuses to listings table (for bulk posting)
        try:
            cursor.execute("SELECT platform_statuses FROM listings LIMIT 1")
        except sqlite3.OperationalError:
            print("Running migration: Adding platform_statuses column to listings table")
            cursor.execute("ALTER TABLE listings ADD COLUMN platform_statuses TEXT")
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
        cursor = self._get_cursor()

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
        cursor = self._get_cursor()

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
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()

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

    def save_deep_analysis(
        self,
        collectible_id: int,
        deep_analysis: Dict[str, Any],
        embedding: Optional[List[float]] = None
    ):
        """Save Claude's deep analysis to a collectible (for RAG)"""
        cursor = self._get_cursor()

        # Convert embedding to JSON string if provided
        embedding_str = json.dumps(embedding) if embedding else None

        # Extract key fields from deep_analysis for quick search
        franchise = None
        rarity_level = None
        if deep_analysis:
            franchise = deep_analysis.get('historical_context', {}).get('franchise') or \
                       deep_analysis.get('franchise')
            rarity_level = deep_analysis.get('rarity', {}).get('rarity_level')

        cursor.execute("""
            UPDATE collectibles
            SET deep_analysis = ?,
                embedding = ?,
                franchise = ?,
                rarity_level = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            json.dumps(deep_analysis),
            embedding_str,
            franchise,
            rarity_level,
            collectible_id
        ))

        self.conn.commit()

    def get_collectible(self, collectible_id: int) -> Optional[Dict]:
        """Get a collectible by ID"""
        cursor = self._get_cursor()
        cursor.execute("SELECT * FROM collectibles WHERE id = ?", (collectible_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def find_similar_collectibles(
        self,
        brand: Optional[str] = None,
        franchise: Optional[str] = None,
        category: Optional[str] = None,
        condition: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Find similar collectibles for RAG context (similarity search).

        This is a simple similarity search based on metadata.
        For production, you'd use vector embeddings + cosine similarity.
        """
        cursor = self._get_cursor()

        # Build query to find similar items
        sql = """
            SELECT *
            FROM collectibles
            WHERE deep_analysis IS NOT NULL
        """
        params = []

        # Priority matching: franchise > brand > category
        if franchise:
            sql += " AND franchise LIKE ?"
            params.append(f"%{franchise}%")
        elif brand:
            sql += " AND brand LIKE ?"
            params.append(f"%{brand}%")
        elif category:
            sql += " AND category LIKE ?"
            params.append(f"%{category}%")

        # Optional condition matching
        if condition:
            sql += " AND condition = ?"
            params.append(condition)

        sql += " ORDER BY times_found DESC, confidence_score DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    # ========================================================================
    # TRAINING DATA METHODS (Knowledge Distillation - Baby Bird Learning)
    # ========================================================================

    def save_training_sample(
        self,
        photo_paths: List[str],
        input_data: Dict[str, Any],
        teacher_output: Dict[str, Any],
        user_id: Optional[int] = None,
        listing_id: Optional[int] = None,
        collectible_id: Optional[int] = None,
        student_output: Optional[Dict[str, Any]] = None,
        student_confidence: Optional[float] = None,
        used_teacher: bool = True
    ) -> int:
        """
        Save a training sample (Claude's analysis as ground truth).

        This builds the dataset for knowledge distillation where:
        - input_data = What the student model will see (Gemini's basic analysis)
        - teacher_output = What Claude said (the correct answer to learn from)
        - student_output = What student model predicted (filled in later during training)
        """
        cursor = self._get_cursor()

        cursor.execute("""
            INSERT INTO training_data (
                user_id, listing_id, collectible_id,
                photo_paths, input_data, teacher_output,
                student_output, student_confidence, used_teacher
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            listing_id,
            collectible_id,
            json.dumps(photo_paths),
            json.dumps(input_data),
            json.dumps(teacher_output),
            json.dumps(student_output) if student_output else None,
            student_confidence,
            used_teacher
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_training_samples(
        self,
        limit: int = 1000,
        offset: int = 0,
        min_quality: Optional[float] = None
    ) -> List[Dict]:
        """Get training samples for model training"""
        cursor = self._get_cursor()

        sql = "SELECT * FROM training_data WHERE 1=1"
        params = []

        if min_quality:
            sql += " AND quality_score >= ?"
            params.append(min_quality)

        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def count_training_samples(self) -> int:
        """Count total training samples (to see if baby bird is ready to fly!)"""
        cursor = self._get_cursor()
        cursor.execute("SELECT COUNT(*) FROM training_data WHERE teacher_output IS NOT NULL")
        return cursor.fetchone()[0]

    def export_training_dataset(self, output_path: str, format: str = "jsonl"):
        """
        Export training data for fine-tuning student model.

        Format options:
        - jsonl: One JSON object per line (for LLaVA, Mistral fine-tuning)
        - hf: HuggingFace datasets format
        """
        import json
        from pathlib import Path

        samples = self.get_training_samples(limit=100000)  # Get all
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if format == "jsonl":
            with open(output_file, 'w') as f:
                for sample in samples:
                    # Format for vision-language model training
                    training_sample = {
                        "id": sample['id'],
                        "images": json.loads(sample['photo_paths']) if sample['photo_paths'] else [],
                        "input": json.loads(sample['input_data']) if sample['input_data'] else {},
                        "output": json.loads(sample['teacher_output']) if sample['teacher_output'] else {},
                        "metadata": {
                            "created_at": sample['created_at'],
                            "used_teacher": sample['used_teacher']
                        }
                    }
                    f.write(json.dumps(training_sample) + '\n')

        print(f"Exported {len(samples)} training samples to {output_file}")
        return len(samples)

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
        status: str = 'draft',
    ) -> int:
        """Create a new listing"""
        cursor = self._get_cursor()

        cursor.execute("""
            INSERT INTO listings (
                listing_uuid, user_id, collectible_id, title, description, price,
                cost, condition, category, item_type, attributes, photos, quantity,
                storage_location, sku, upc, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            listing_uuid, user_id, collectible_id, title, description, price,
            cost, condition, category, item_type,
            json.dumps(attributes) if attributes else None,
            json.dumps(photos),
            quantity,
            storage_location,
            sku,
            upc,
            status,
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_listing(self, listing_id: int) -> Optional[Dict]:
        """Get a listing by ID"""
        cursor = self._get_cursor()
        cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_listing_by_uuid(self, listing_uuid: str) -> Optional[Dict]:
        """Get a listing by UUID"""
        cursor = self._get_cursor()
        cursor.execute("SELECT * FROM listings WHERE listing_uuid = ?", (listing_uuid,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_drafts(self, limit: int = 100, user_id: Optional[int] = None) -> List[Dict]:
        """Get all draft listings, optionally filtered by user"""
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE listings
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, listing_id))
        self.conn.commit()

    def delete_listing(self, listing_id: int):
        """Delete a listing and its platform listings"""
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()

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
        cursor = self._get_cursor()

        if self.is_postgres:
            cursor.execute("""
                INSERT INTO platform_listings (
                    listing_id, platform, platform_listing_id,
                    platform_url, status, posted_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (listing_id, platform) DO UPDATE SET
                    platform_listing_id = EXCLUDED.platform_listing_id,
                    platform_url = EXCLUDED.platform_url,
                    status = EXCLUDED.status,
                    posted_at = CURRENT_TIMESTAMP
            """, (listing_id, platform, platform_listing_id, platform_url, status))
        else:
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
        cursor = self._get_cursor()

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
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM platform_listings WHERE listing_id = ?
        """, (listing_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_active_listings_by_platform(self, platform: str) -> List[Dict]:
        """Get all active listings for a specific platform"""
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()
        cursor.execute("""
            INSERT INTO notifications (
                type, listing_id, platform, title, message, data
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (type, listing_id, platform, title, message, json.dumps(data) if data else None))
        self.conn.commit()
        return cursor.lastrowid

    def get_unread_notifications(self) -> List[Dict]:
        """Get all unread notifications"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM notifications
            WHERE is_read = 0
            ORDER BY created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def mark_notification_read(self, notification_id: int):
        """Mark a notification as read"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE notifications
            SET is_read = 1
            WHERE id = ?
        """, (notification_id,))
        self.conn.commit()

    def mark_notification_emailed(self, notification_id: int):
        """Mark a notification as emailed"""
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()
        cursor.execute("""
            INSERT INTO price_alerts (collectible_id, target_price, condition)
            VALUES (?, ?, ?)
        """, (collectible_id, target_price, condition))
        self.conn.commit()
        return cursor.lastrowid

    def get_active_price_alerts(self) -> List[Dict]:
        """Get all active price alerts"""
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        """, (username, email, password_hash))
        self.conn.commit()
        return cursor.lastrowid

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        cursor = self._get_cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        cursor = self._get_cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        cursor = self._get_cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user_id,))
        self.conn.commit()

    def update_notification_email(self, user_id: int, notification_email: str):
        """Update user's notification email"""
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()

        if self.is_postgres:
            cursor.execute("""
                INSERT INTO marketplace_credentials
                (user_id, platform, username, password, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, platform) DO UPDATE SET
                    username = EXCLUDED.username,
                    password = EXCLUDED.password,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, platform, username, password))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO marketplace_credentials
                (user_id, platform, username, password, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, platform, username, password))

        self.conn.commit()

    def get_marketplace_credentials(self, user_id: int, platform: str) -> Optional[Dict]:
        """Get marketplace credentials for a specific platform"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM marketplace_credentials
            WHERE user_id = ? AND platform = ?
        """, (user_id, platform))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_marketplace_credentials(self, user_id: int) -> List[Dict]:
        """Get all marketplace credentials for a user"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM marketplace_credentials
            WHERE user_id = ?
            ORDER BY platform
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]

    def delete_marketplace_credentials(self, user_id: int, platform: str):
        """Delete marketplace credentials for a platform"""
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM activity_logs WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchone()[0]

    # ========================================================================
    # ADMIN METHODS
    # ========================================================================

    def get_all_users(self, include_inactive: bool = False) -> List[Dict]:
        """Get all users (admin function)"""
        cursor = self._get_cursor()
        if include_inactive:
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM users WHERE is_active = 1 ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def toggle_user_admin(self, user_id: int) -> bool:
        """Toggle admin status for a user"""
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()
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
        cursor = self._get_cursor()

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
        cursor = self._get_cursor()

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
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE users
            SET verification_token = ?
            WHERE id = ?
        """, (token, user_id))
        self.conn.commit()

    def verify_email(self, token: str) -> bool:
        """Verify email with token"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE users
            SET email_verified = 1, verification_token = NULL
            WHERE verification_token = ?
        """, (token,))
        self.conn.commit()
        return cursor.rowcount > 0

    def set_reset_token(self, user_id: int, token: str, expiry_hours: int = 24):
        """Set password reset token"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE users
            SET reset_token = ?,
                reset_token_expiry = datetime('now', '+' || ? || ' hours')
            WHERE id = ?
        """, (token, expiry_hours, user_id))
        self.conn.commit()

    def verify_reset_token(self, token: str) -> Optional[Dict]:
        """Verify reset token and return user if valid"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM users
            WHERE reset_token = ?
            AND reset_token_expiry > datetime('now')
        """, (token,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_password(self, user_id: int, new_password_hash: str):
        """Update user password and clear reset token"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE users
            SET password_hash = ?,
                reset_token = NULL,
                reset_token_expiry = NULL
            WHERE id = ?
        """, (new_password_hash, user_id))
        self.conn.commit()

    # ========================================================================
    # PLATFORM ACTIVITY MONITORING METHODS
    # ========================================================================

    def add_platform_activity(
        self,
        user_id: int,
        platform: str,
        activity_type: str,
        platform_listing_id: Optional[str] = None,
        listing_id: Optional[int] = None,
        title: Optional[str] = None,
        buyer_username: Optional[str] = None,
        message_text: Optional[str] = None,
        sold_price: Optional[float] = None,
        activity_date: Optional[str] = None,
        raw_data: Optional[str] = None
    ) -> int:
        """
        Add platform activity (sold item, message, offer, etc.)

        Args:
            user_id: User ID
            platform: Platform name (ebay, mercari, etc.)
            activity_type: Type of activity (sold, message, offer, view, favorite)
            platform_listing_id: ID of listing on that platform
            listing_id: Our internal listing ID (if matched)
            title: Item title
            buyer_username: Buyer's username (if applicable)
            message_text: Message content (for messages)
            sold_price: Sale price (for sold items)
            activity_date: When activity occurred
            raw_data: JSON with full data from platform

        Returns:
            Activity ID
        """
        cursor = self._get_cursor()
        cursor.execute("""
            INSERT INTO platform_activity (
                user_id, platform, activity_type, platform_listing_id,
                listing_id, title, buyer_username, message_text,
                sold_price, activity_date, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, platform, activity_type, platform_listing_id,
            listing_id, title, buyer_username, message_text,
            sold_price, activity_date or datetime.now().isoformat(), raw_data
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_platform_activity(
        self,
        user_id: int,
        limit: int = 50,
        unread_only: bool = False,
        activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get platform activity for a user

        Args:
            user_id: User ID
            limit: Max activities to return
            unread_only: Only return unread activities
            activity_type: Filter by type (sold, message, etc.)

        Returns:
            List of activity dicts
        """
        cursor = self._get_cursor()

        query = """
            SELECT * FROM platform_activity
            WHERE user_id = ?
        """
        params = [user_id]

        if unread_only:
            query += " AND is_read = 0"

        if activity_type:
            query += " AND activity_type = ?"
            params.append(activity_type)

        query += " ORDER BY activity_date DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def mark_activity_read(self, activity_id: int):
        """Mark platform activity as read"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE platform_activity
            SET is_read = 1
            WHERE id = ?
        """, (activity_id,))
        self.conn.commit()

    def sync_sold_activity_to_inventory(self, activity_id: int):
        """
        Sync sold activity to inventory (mark listing as sold)

        Args:
            activity_id: Platform activity ID

        Returns:
            True if successful
        """
        cursor = self._get_cursor()

        # Get activity
        cursor.execute("SELECT * FROM platform_activity WHERE id = ?", (activity_id,))
        activity = cursor.fetchone()

        if not activity or activity['activity_type'] != 'sold':
            return False

        listing_id = activity['listing_id']
        if not listing_id:
            return False

        # Mark listing as sold
        cursor.execute("""
            UPDATE listings
            SET status = 'sold',
                sold_platform = ?,
                sold_date = ?,
                sold_price = ?
            WHERE id = ?
        """, (
            activity['platform'],
            activity['activity_date'],
            activity['sold_price'],
            listing_id
        ))

        # Mark activity as synced
        cursor.execute("""
            UPDATE platform_activity
            SET is_synced_to_inventory = 1
            WHERE id = ?
        """, (activity_id,))

        self.conn.commit()
        return True

    def check_duplicate_on_platform(
        self,
        user_id: int,
        platform: str,
        title: str,
        upc: Optional[str] = None,
        sku: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if item already exists on a platform (duplicate detection)

        Args:
            user_id: User ID
            platform: Platform to check
            title: Item title
            upc: UPC code (stronger match)
            sku: SKU (stronger match)

        Returns:
            Existing listing dict if duplicate found, None otherwise
        """
        cursor = self._get_cursor()

        # First try exact match by UPC or SKU (strongest signal)
        if upc or sku:
            query = """
                SELECT l.*
                FROM listings l
                JOIN platform_listings pl ON l.id = pl.listing_id
                WHERE l.user_id = ?
                AND pl.platform = ?
                AND pl.status IN ('active', 'pending')
                AND (l.upc = ? OR l.sku = ?)
                LIMIT 1
            """
            cursor.execute(query, (user_id, platform, upc or '', sku or ''))
            row = cursor.fetchone()
            if row:
                return dict(row)

        # Fuzzy match by title (title similarity > 80%)
        query = """
            SELECT l.*, pl.platform_listing_id, pl.status as platform_status
            FROM listings l
            JOIN platform_listings pl ON l.id = pl.listing_id
            WHERE l.user_id = ?
            AND pl.platform = ?
            AND pl.status IN ('active', 'pending')
            AND LOWER(l.title) LIKE LOWER(?)
        """
        # Simple fuzzy match - look for titles that contain most of the words
        search_pattern = f"%{title[:50]}%"
        cursor.execute(query, (user_id, platform, search_pattern))
        row = cursor.fetchone()

        return dict(row) if row else None

    # ========================================================================
    # STORAGE SYSTEM METHODS (Standalone Organization Tool)
    # ========================================================================

    def create_storage_bin(
        self,
        user_id: int,
        bin_name: str,
        bin_type: str,
        description: Optional[str] = None
    ) -> int:
        """
        Create a new storage bin

        Args:
            user_id: User ID
            bin_name: Bin name (e.g., 'A', 'B', 'Shoes')
            bin_type: 'clothing' or 'cards'
            description: Optional description

        Returns:
            Bin ID
        """
        cursor = self._get_cursor()
        cursor.execute("""
            INSERT INTO storage_bins (user_id, bin_name, bin_type, description)
            VALUES (?, ?, ?, ?)
        """, (user_id, bin_name, bin_type, description))
        self.conn.commit()
        return cursor.lastrowid

    def get_storage_bins(self, user_id: int, bin_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all storage bins for a user"""
        cursor = self._get_cursor()

        if bin_type:
            cursor.execute("""
                SELECT * FROM storage_bins
                WHERE user_id = ? AND bin_type = ?
                ORDER BY bin_name
            """, (user_id, bin_type))
        else:
            cursor.execute("""
                SELECT * FROM storage_bins
                WHERE user_id = ?
                ORDER BY bin_type, bin_name
            """, (user_id,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def create_storage_section(
        self,
        bin_id: int,
        section_name: str,
        capacity: Optional[int] = None
    ) -> int:
        """
        Create a section within a bin

        Args:
            bin_id: Bin ID
            section_name: Section name (e.g., 'A1', '1')
            capacity: Max items (optional)

        Returns:
            Section ID
        """
        cursor = self._get_cursor()
        cursor.execute("""
            INSERT INTO storage_sections (bin_id, section_name, capacity)
            VALUES (?, ?, ?)
        """, (bin_id, section_name, capacity))
        self.conn.commit()
        return cursor.lastrowid

    def get_storage_sections(self, bin_id: int) -> List[Dict[str, Any]]:
        """Get all sections for a bin"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM storage_sections
            WHERE bin_id = ?
            ORDER BY section_name
        """, (bin_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def generate_storage_id(
        self,
        user_id: int,
        bin_name: str,
        section_name: Optional[str] = None,
        category: Optional[str] = None
    ) -> str:
        """
        Generate next available storage ID

        Args:
            user_id: User ID
            bin_name: Bin name (e.g., 'A')
            section_name: Section name (e.g., 'A1', optional)
            category: Card category (e.g., 'FB', 'PKMN', optional)

        Returns:
            Storage ID (e.g., 'A2-14', 'FB-A1-12')
        """
        cursor = self._get_cursor()

        # Build pattern based on inputs
        if category:
            # Card format: FB-A1-##
            pattern = f"{category}-{bin_name}{section_name or ''}-%"
        elif section_name:
            # Bin+Section format: A1-##
            pattern = f"{bin_name}{section_name}-%"
        else:
            # Bin only format: A-##
            pattern = f"{bin_name}-%"

        # Find highest existing number
        cursor.execute("""
            SELECT storage_id FROM storage_items
            WHERE user_id = ? AND storage_id LIKE ?
            ORDER BY storage_id DESC
            LIMIT 1
        """, (user_id, pattern))

        row = cursor.fetchone()

        if row:
            # Extract number from last ID and increment
            last_id = row['storage_id']
            try:
                # Get the number after the last dash
                last_num = int(last_id.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

        # Generate new ID
        if category:
            return f"{category}-{bin_name}{section_name or ''}-{next_num:02d}"
        elif section_name:
            return f"{bin_name}{section_name}-{next_num:02d}"
        else:
            return f"{bin_name}-{next_num:02d}"

    def add_storage_item(
        self,
        user_id: int,
        storage_id: str,
        bin_id: int,
        section_id: Optional[int] = None,
        item_type: Optional[str] = None,
        category: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        quantity: int = 1,
        photos: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Add item to storage

        Args:
            user_id: User ID
            storage_id: Unique storage ID (e.g., 'A2-14')
            bin_id: Bin ID
            section_id: Section ID (optional)
            item_type: Item type (clothing, shoes, card, etc.)
            category: Card category (FB, PKMN, etc.)
            title: Item title/name
            description: Description
            quantity: Quantity
            photos: Photo paths
            notes: Additional notes

        Returns:
            Storage item ID
        """
        cursor = self._get_cursor()

        photos_json = json.dumps(photos) if photos else None

        cursor.execute("""
            INSERT INTO storage_items (
                user_id, storage_id, bin_id, section_id, item_type,
                category, title, description, quantity, photos, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, storage_id, bin_id, section_id, item_type,
            category, title, description, quantity, photos_json, notes
        ))

        # Update section item count
        if section_id:
            cursor.execute("""
                UPDATE storage_sections
                SET item_count = item_count + ?
                WHERE id = ?
            """, (quantity, section_id))

        self.conn.commit()
        return cursor.lastrowid

    def find_storage_item(self, user_id: int, storage_id: str) -> Optional[Dict[str, Any]]:
        """Find item by storage ID"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT si.*, sb.bin_name, sb.bin_type, ss.section_name
            FROM storage_items si
            JOIN storage_bins sb ON si.bin_id = sb.id
            LEFT JOIN storage_sections ss ON si.section_id = ss.id
            WHERE si.user_id = ? AND si.storage_id = ?
        """, (user_id, storage_id))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_storage_items(
        self,
        user_id: int,
        bin_id: Optional[int] = None,
        section_id: Optional[int] = None,
        item_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get storage items with filters

        Args:
            user_id: User ID
            bin_id: Filter by bin
            section_id: Filter by section
            item_type: Filter by type
            limit: Max items to return

        Returns:
            List of storage items
        """
        cursor = self._get_cursor()

        query = """
            SELECT si.*, sb.bin_name, sb.bin_type, ss.section_name
            FROM storage_items si
            JOIN storage_bins sb ON si.bin_id = sb.id
            LEFT JOIN storage_sections ss ON si.section_id = ss.id
            WHERE si.user_id = ?
        """
        params = [user_id]

        if bin_id:
            query += " AND si.bin_id = ?"
            params.append(bin_id)

        if section_id:
            query += " AND si.section_id = ?"
            params.append(section_id)

        if item_type:
            query += " AND si.item_type = ?"
            params.append(item_type)

        query += " ORDER BY si.created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_storage_map(self, user_id: int) -> Dict[str, Any]:
        """
        Get complete storage map (bins, sections, item counts)

        Returns:
            {
                'clothing_bins': [...],
                'card_bins': [...],
                'total_items': 123
            }
        """
        cursor = self._get_cursor()

        # Get all bins with section counts
        cursor.execute("""
            SELECT
                sb.*,
                COUNT(DISTINCT ss.id) as section_count,
                COALESCE(SUM(ss.item_count), 0) as total_items
            FROM storage_bins sb
            LEFT JOIN storage_sections ss ON sb.id = ss.bin_id
            WHERE sb.user_id = ?
            GROUP BY sb.id
            ORDER BY sb.bin_type, sb.bin_name
        """, (user_id,))

        bins = [dict(row) for row in cursor.fetchall()]

        # Group by type
        clothing_bins = [b for b in bins if b['bin_type'] == 'clothing']
        card_bins = [b for b in bins if b['bin_type'] == 'cards']

        # Get sections for each bin
        for bin_data in bins:
            sections = self.get_storage_sections(bin_data['id'])
            bin_data['sections'] = sections

        # Total items
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM storage_items
            WHERE user_id = ?
        """, (user_id,))
        total_items = cursor.fetchone()['total']

        return {
            'clothing_bins': clothing_bins,
            'card_bins': card_bins,
            'total_items': total_items
        }

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
