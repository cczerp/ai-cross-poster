"""
PostgreSQL Database Handler for AI Cross-Poster
All SQLite code removed - PostgreSQL only
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import psycopg2
import psycopg2.extras
import psycopg2.pool


# Global connection pool - shared across all Database instances
_connection_pool = None

def _get_connection_pool():
    """Get or create global connection pool"""
    global _connection_pool
    if _connection_pool is None:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError(
                "DATABASE_URL environment variable is required. "
                "Set it to your PostgreSQL connection string:\n"
                "postgresql://user:password@host:5432/database"
            )
        
        # Parse connection string for pool
        connection_params = database_url
        
        # Ensure SSL mode is set
        if '?' not in connection_params:
            connection_params += '?sslmode=require&connect_timeout=10'
        else:
            if 'sslmode=' not in connection_params:
                connection_params += '&sslmode=require'
            if 'connect_timeout=' not in connection_params:
                connection_params += '&connect_timeout=10'
        
        # Create connection pool with resilient settings
        # Keepalives prevent Render from closing idle SSL connections
        print("🔌 Creating PostgreSQL connection pool...", flush=True)
        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,  # Minimum connections in pool
            maxconn=20,  # Maximum connections (increased for resilience)
            dsn=connection_params,
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )
        print("✅ Connection pool created", flush=True)
    
    return _connection_pool


class Database:
    """Main database handler for AI Cross-Poster - PostgreSQL only with connection pooling"""

    def __init__(self, db_path: str = None):
        """Initialize Database instance - uses global connection pool"""
        self.cursor_factory = psycopg2.extras.RealDictCursor
        self.pool = _get_connection_pool()

        # Get a dedicated connection from the pool for this Database instance
        # This connection will be held for the lifetime of the Database object
        self.conn = None
        self._get_connection_from_pool()

        # Mark OAuth migration as not checked yet
        self._oauth_columns_checked = False

    def close(self):
        """Return connection to pool - should be called when done with Database instance"""
        if self.conn is not None:
            try:
                if not self.conn.closed:
                    # Rollback any pending transactions
                    try:
                        self.conn.rollback()
                    except:
                        pass
                # Return connection to pool
                self.pool.putconn(self.conn)
            except Exception as e:
                # If we can't return to pool, try to close it
                try:
                    self.conn.close()
                except:
                    pass
            finally:
                self.conn = None

    def __del__(self):
        """Cleanup - return connection to pool when Database instance is garbage collected"""
        try:
            self.close()
        except:
            pass

    def _ensure_oauth_columns(self):
        """Ensure OAuth-related columns exist in users table (automatic migration)"""
        max_retries = 2  # Reduced retries for faster startup
        retry_count = 0

        while retry_count < max_retries:
            try:
                cursor = self._get_cursor()

                # Add supabase_uid column if it doesn't exist
                cursor.execute("""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS supabase_uuid TEXT;
                """)

                # Add oauth_provider column if it doesn't exist
                cursor.execute("""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider TEXT;
                """)

                # Make password_hash nullable for OAuth users
                cursor.execute("""
                    ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
                """)

                self.conn.commit()
                if cursor:
                    cursor.close()
                self._oauth_columns_checked = True  # Mark as checked
                print("✅ OAuth columns migration complete")
                return  # Success, exit

            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                # Connection errors - retry with reconnection
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
                retry_count += 1
                if retry_count == 1:  # Only log first attempt to reduce noise
                    print(f"⚠️  Migration connection error: {type(e).__name__}")

                # Try to rollback if connection still exists
                try:
                    if self.conn and not self.conn.closed:
                        self.conn.rollback()
                except:
                    pass

                # Fast retry for startup
                if retry_count < max_retries:
                    wait_time = 0.5 * retry_count  # Progressive backoff
                    if retry_count < 2:  # Only log first retry
                        print(f"⏳ Retrying migration in {wait_time:.1f}s... (attempt {retry_count}/{max_retries})")
                    time.sleep(wait_time)

                    # Reconnect before retrying
                    try:
                        if self.conn and not self.conn.closed:
                            # Return connection to pool and get a new one
                            self.pool.putconn(self.conn, close=True)
                            self.conn = None
                    except:
                        pass
                    try:
                        self._get_connection_from_pool()
                        time.sleep(0.2)  # Let connection stabilize
                    except Exception as conn_err:
                        if retry_count >= max_retries - 1:  # Only log if this is final attempt
                            print(f"⚠️  Migration reconnection failed: {conn_err}")
                            print(f"⚠️  Skipping OAuth migration - will retry on next request")
                        return
                else:
                    # Don't block - migration can happen later on first actual query
                    # Mark as attempted so we don't spam retries
                    self._oauth_columns_checked = True
                    return

            except Exception as e:
                # Other errors - try to rollback and log
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
                try:
                    if self.conn and not self.conn.closed:
                        self.conn.rollback()
                except:
                    pass
                # Don't log non-critical migration errors during startup
                # print(f"Note: OAuth columns migration: {e}")
                return  # Non-critical, continue

    def _get_connection_from_pool(self):
        """Get a connection from pool and store it as self.conn"""
        try:
            # If we already have a connection, return the old one to pool first
            if self.conn is not None and not self.conn.closed:
                try:
                    self.pool.putconn(self.conn)
                except:
                    pass

            # Get fresh connection from pool
            self.conn = self.pool.getconn()
            if self.conn.closed:
                # Connection is closed, return it to pool and get a new one
                self.pool.putconn(self.conn, close=True)
                self.conn = self.pool.getconn()

            print(f"✅ Connection acquired from pool", flush=True)

        except Exception as e:
            print(f"❌ Failed to get connection from pool: {e}", flush=True)
            raise

    def _commit_read(self):
        """Commit or rollback after read operations to close transaction"""
        try:
            if self.conn and not self.conn.closed:
                self.conn.rollback()  # Use rollback for reads (safer than commit)
        except Exception as e:
            # Ignore errors - connection might be in bad state
            pass

    def _get_cursor(self, retries=3):
        """Get PostgreSQL cursor from self.conn - returns cursor only (not tuple)"""
        for attempt in range(retries):
            try:
                # Ensure we have a valid connection
                if self.conn is None or self.conn.closed:
                    self._get_connection_from_pool()

                # Return cursor for use
                cursor = self.conn.cursor(cursor_factory=self.cursor_factory)
                return cursor
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                print(f"⚠️  Connection error (attempt {attempt + 1}/{retries}): {e}")
                # Connection error - force close and get a new connection
                if self.conn:
                    try:
                        # Return bad connection to pool (will be closed)
                        self.pool.putconn(self.conn, close=True)
                    except:
                        pass
                    self.conn = None

                if attempt < retries - 1:
                    # Wait before retrying (exponential backoff)
                    wait_time = 0.5 * (2 ** attempt)
                    time.sleep(wait_time)
                    # Force get a fresh connection for next attempt
                    try:
                        self._get_connection_from_pool()
                        print(f"✅ Got fresh connection from pool")
                    except Exception as conn_err:
                        print(f"❌ Failed to get connection: {conn_err}")
                        pass
                else:
                    print(f"❌ Failed after {retries} attempts")
                    raise
            except Exception as e:
                print(f"❌ Unexpected error in _get_cursor: {e}")
                raise
    
    def _return_connection(self, conn, commit=True, error=False):
        """Return connection to pool - DEPRECATED: Now using per-instance connections"""
        # This method is deprecated but kept for backward compatibility
        # with old code that still calls it. It's a no-op now.
        if conn is None:
            return
        try:
            if error:
                try:
                    conn.rollback()
                except:
                    pass
            elif commit:
                try:
                    conn.commit()
                except:
                    try:
                        conn.rollback()
                    except:
                        pass
            self.pool.putconn(conn)
        except Exception as e:
            # If we can't return to pool, try to close it
            try:
                conn.close()
            except:
                pass
    
    def _with_connection(self, func, commit=True):
        """Context manager pattern for database operations"""
        cursor = None
        try:
            cursor = self._get_cursor()
            result = func(cursor)
            if commit:
                self.conn.commit()
            return result
        except Exception as e:
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            raise
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass

    def _create_tables(self):
        """Create all database tables"""
        cursor = self._get_cursor()
        try:
            # Users table - for authentication (UUID primary key)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    supabase_uid TEXT,
                    oauth_provider TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    tier TEXT DEFAULT 'FREE',
                    notification_email TEXT,
                    email_verified BOOLEAN DEFAULT FALSE,
                    verification_token TEXT,
                    reset_token TEXT,
                    reset_token_expiry TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)

            # Enable UUID extension if not already enabled
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
            except Exception:
                pass

            # Add supabase_uid column if it doesn't exist (migration)
            cursor.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS supabase_uid TEXT;
            """)

            # Add oauth_provider column if it doesn't exist (migration)
            cursor.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider TEXT;
            """)

            # Make password_hash nullable for OAuth users (migration)
            cursor.execute("""
                ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
            """)

            # Marketplace credentials - per user
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS marketplace_credentials (
                    id SERIAL PRIMARY KEY,
                    user_id UUID NOT NULL,
                    platform TEXT NOT NULL,
                    username TEXT,
                    password TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, platform)
                )
            """)

            # Collectibles database table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collectibles (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT,
                    brand TEXT,
                    model TEXT,
                    year INTEGER,
                    condition TEXT,
                    estimated_value_low REAL,
                    estimated_value_high REAL,
                    estimated_value_avg REAL,
                    market_data TEXT,
                    attributes TEXT,
                    image_urls TEXT,
                    identified_by TEXT,
                    confidence_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    times_found INTEGER DEFAULT 1,
                    notes TEXT,
                    deep_analysis TEXT,
                    embedding TEXT,
                    franchise TEXT,
                    rarity_level TEXT
                )
            """)

            # Listings table - tracks all your listings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS listings (
                    id SERIAL PRIMARY KEY,
                    listing_uuid TEXT UNIQUE NOT NULL,
                    user_id UUID NOT NULL,
                    collectible_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    price REAL NOT NULL,
                    cost REAL,
                    condition TEXT,
                    category TEXT,
                    item_type TEXT,
                    attributes TEXT,
                    photos TEXT,
                    quantity INTEGER DEFAULT 1,
                    storage_location TEXT,
                    sku TEXT,
                    upc TEXT,
                    status TEXT DEFAULT 'draft',
                    sold_platform TEXT,
                    sold_date TIMESTAMP,
                    sold_price REAL,
                    platform_statuses TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (collectible_id) REFERENCES collectibles(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Training data table - Knowledge Distillation
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_data (
                    id SERIAL PRIMARY KEY,
                    user_id UUID,
                    listing_id INTEGER,
                    collectible_id INTEGER,
                    photo_paths TEXT,
                    input_data TEXT,
                    teacher_output TEXT,
                    student_output TEXT,
                    student_confidence REAL,
                    used_teacher BOOLEAN DEFAULT TRUE,
                    quality_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (listing_id) REFERENCES listings(id),
                    FOREIGN KEY (collectible_id) REFERENCES collectibles(id)
                )
            """)

            # Create index for faster training data queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_data_created
                ON training_data(created_at DESC)
            """)

            # Platform listings - track where each listing is posted
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_listings (
                    id SERIAL PRIMARY KEY,
                    listing_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    platform_listing_id TEXT,
                    platform_url TEXT,
                    status TEXT DEFAULT 'pending',
                    posted_at TIMESTAMP,
                    last_synced TIMESTAMP,
                    cancel_scheduled_at TIMESTAMP,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    FOREIGN KEY (listing_id) REFERENCES listings(id),
                    UNIQUE(listing_id, platform)
                )
            """)

            # Sync log - track all sync operations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_log (
                    id SERIAL PRIMARY KEY,
                    listing_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (listing_id) REFERENCES listings(id)
                )
            """)

            # Platform activity - monitor external platforms
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_activity (
                    id SERIAL PRIMARY KEY,
                    user_id UUID NOT NULL,
                    platform TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    platform_listing_id TEXT,
                    listing_id INTEGER,
                    title TEXT,
                    buyer_username TEXT,
                    message_text TEXT,
                    sold_price REAL,
                    activity_date TIMESTAMP,
                    is_read BOOLEAN DEFAULT FALSE,
                    is_synced_to_inventory BOOLEAN DEFAULT FALSE,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (listing_id) REFERENCES listings(id)
                )
            """)

            # Create index for faster activity queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_platform_activity_user_unread
                ON platform_activity(user_id, is_read, created_at DESC)
            """)

            # ===== MIGRATION: Add tier column if it doesn't exist =====
            try:
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name='users' AND column_name='tier'
                """)
                if not cursor.fetchone():
                    cursor.execute("""
                        ALTER TABLE users
                        ADD COLUMN tier TEXT DEFAULT 'FREE'
                    """)
            except Exception as e:
                print(f"⚠️  Tier column migration skipped: {e}")

            # Storage bins - for physical organization
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS storage_bins (
                    id SERIAL PRIMARY KEY,
                    user_id UUID NOT NULL,
                    bin_name TEXT NOT NULL,
                    bin_type TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, bin_name, bin_type)
                )
            """)

            # Storage sections - compartments within bins
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS storage_sections (
                    id SERIAL PRIMARY KEY,
                    bin_id INTEGER NOT NULL,
                    section_name TEXT NOT NULL,
                    capacity INTEGER,
                    item_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bin_id) REFERENCES storage_bins(id),
                    UNIQUE(bin_id, section_name)
                )
            """)

            # Storage items - physical items in storage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS storage_items (
                    id SERIAL PRIMARY KEY,
                    user_id UUID NOT NULL,
                    storage_id TEXT UNIQUE NOT NULL,
                    bin_id INTEGER NOT NULL,
                    section_id INTEGER,
                    item_type TEXT,
                    category TEXT,
                    title TEXT,
                    description TEXT,
                    quantity INTEGER DEFAULT 1,
                    photos TEXT,
                    notes TEXT,
                    listing_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (bin_id) REFERENCES storage_bins(id),
                    FOREIGN KEY (section_id) REFERENCES storage_sections(id),
                    FOREIGN KEY (listing_id) REFERENCES listings(id)
                )
            """)

            # Create indexes for faster storage queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_storage_items_user
                ON storage_items(user_id, created_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_storage_items_bin_section
                ON storage_items(bin_id, section_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_storage_items_storage_id
                ON storage_items(storage_id)
            """)

            # Card collections - unified card data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_collections (
                    id SERIAL PRIMARY KEY,
                    user_id UUID NOT NULL,
                    card_uuid TEXT UNIQUE NOT NULL,
                    card_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    card_number TEXT,
                    quantity INTEGER DEFAULT 1,
                    organization_mode TEXT,
                    primary_category TEXT,
                    custom_categories TEXT,
                    storage_location TEXT,
                    storage_item_id INTEGER,
                    game_name TEXT,
                    set_name TEXT,
                    set_code TEXT,
                    set_symbol TEXT,
                    rarity TEXT,
                    card_subtype TEXT,
                    format_legality TEXT,
                    sport TEXT,
                    year INTEGER,
                    brand TEXT,
                    series TEXT,
                    player_name TEXT,
                    team TEXT,
                    is_rookie_card BOOLEAN DEFAULT FALSE,
                    parallel_color TEXT,
                    insert_series TEXT,
                    grading_company TEXT,
                    grading_score REAL,
                    grading_serial TEXT,
                    estimated_value REAL,
                    value_tier TEXT,
                    purchase_price REAL,
                    photos TEXT,
                    notes TEXT,
                    ai_identified BOOLEAN DEFAULT FALSE,
                    ai_confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (storage_item_id) REFERENCES storage_items(id)
                )
            """)

            # Organization presets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_organization_presets (
                    id SERIAL PRIMARY KEY,
                    user_id UUID NOT NULL,
                    preset_name TEXT NOT NULL,
                    card_type_filter TEXT,
                    organization_mode TEXT NOT NULL,
                    sort_order TEXT,
                    filters TEXT,
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, preset_name)
                )
            """)

            # Custom categories
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_custom_categories (
                    id SERIAL PRIMARY KEY,
                    user_id UUID NOT NULL,
                    category_name TEXT NOT NULL,
                    category_color TEXT,
                    category_icon TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, category_name)
                )
            """)

            # Card collection indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_card_collections_user
                ON card_collections(user_id, created_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_card_collections_type
                ON card_collections(card_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_card_collections_org_mode
                ON card_collections(organization_mode, primary_category)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_card_collections_set
                ON card_collections(set_code, card_number)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_card_collections_sport_year
                ON card_collections(sport, year, brand)
            """)

            # Notifications/alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    type TEXT NOT NULL,
                    listing_id INTEGER,
                    platform TEXT,
                    title TEXT NOT NULL,
                    message TEXT,
                    data TEXT,
                    is_read BOOLEAN DEFAULT FALSE,
                    sent_email BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (listing_id) REFERENCES listings(id)
                )
            """)

            # Price alerts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id SERIAL PRIMARY KEY,
                    collectible_id INTEGER NOT NULL,
                    target_price REAL NOT NULL,
                    condition TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (collectible_id) REFERENCES collectibles(id)
                )
            """)

            # Activity logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id SERIAL PRIMARY KEY,
                    user_id UUID,
                    action TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id INTEGER,
                    details TEXT,
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
                CREATE INDEX IF NOT EXISTS idx_listings_user_id
                ON listings(user_id)
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

            # Mobile app tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    storage_location TEXT,
                    photos TEXT,  -- JSON array of photo objects
                    barcode TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    brand TEXT,
                    size TEXT,
                    color TEXT,
                    condition TEXT DEFAULT 'good',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Commit all schema work in one transaction
            self.conn.commit()
            print("✅ PostgreSQL tables created successfully")
        except Exception as e:
            try:
                if self.conn and not self.conn.closed:
                    self.conn.rollback()
            except Exception:
                pass
            print(f"Error creating tables: {e}")
            raise
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

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
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            name, category, brand, model, year, condition,
            estimated_value_low, estimated_value_high, avg_value,
            json.dumps(market_data) if market_data else None,
            json.dumps(attributes) if attributes else None,
            json.dumps(image_urls) if image_urls else None,
            identified_by, confidence_score, notes
        ))

        result = cursor.fetchone()
        self.conn.commit()
        return result['id']

    def find_collectible(self, name: str, brand: Optional[str] = None) -> Optional[Dict]:
        """Find a collectible by name and optional brand"""
        cursor = self._get_cursor()

        if brand:
            cursor.execute("""
                SELECT * FROM collectibles
                WHERE name ILIKE %s AND brand ILIKE %s
                ORDER BY times_found DESC, confidence_score DESC
                LIMIT 1
            """, (f"%{name}%", f"%{brand}%"))
        else:
            cursor.execute("""
                SELECT * FROM collectibles
                WHERE name ILIKE %s
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
            WHERE id = %s
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
            sql += " AND (name ILIKE %s OR brand ILIKE %s OR model ILIKE %s)"
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])

        if category:
            sql += " AND category ILIKE %s"
            params.append(f"%{category}%")

        if brand:
            sql += " AND brand ILIKE %s"
            params.append(f"%{brand}%")

        if min_value:
            sql += " AND estimated_value_avg >= %s"
            params.append(min_value)

        if max_value:
            sql += " AND estimated_value_avg <= %s"
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

        embedding_str = json.dumps(embedding) if embedding else None

        franchise = None
        rarity_level = None
        if deep_analysis:
            franchise = deep_analysis.get('historical_context', {}).get('franchise') or \
                       deep_analysis.get('franchise')
            rarity_level = deep_analysis.get('rarity', {}).get('rarity_level')

        cursor.execute("""
            UPDATE collectibles
            SET deep_analysis = %s,
                embedding = %s,
                franchise = %s,
                rarity_level = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
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
        cursor.execute("SELECT * FROM collectibles WHERE id = %s", (collectible_id,))
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
        """Find similar collectibles for RAG context"""
        cursor = self._get_cursor()

        sql = """
            SELECT *
            FROM collectibles
            WHERE deep_analysis IS NOT NULL
        """
        params = []

        if franchise:
            sql += " AND franchise ILIKE %s"
            params.append(f"%{franchise}%")
        elif brand:
            sql += " AND brand ILIKE %s"
            params.append(f"%{brand}%")
        elif category:
            sql += " AND category ILIKE %s"
            params.append(f"%{category}%")

        if condition:
            sql += " AND condition = %s"
            params.append(condition)

        sql += " ORDER BY times_found DESC, confidence_score DESC LIMIT %s"
        params.append(limit)

        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    # ========================================================================
    # TRAINING DATA METHODS
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
        """Save a training sample"""
        cursor = self._get_cursor()

        cursor.execute("""
            INSERT INTO training_data (
                user_id, listing_id, collectible_id,
                photo_paths, input_data, teacher_output,
                student_output, student_confidence, used_teacher
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
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

        result = cursor.fetchone()
        self.conn.commit()
        return result['id']

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
            sql += " AND quality_score >= %s"
            params.append(min_quality)

        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def count_training_samples(self) -> int:
        """Count total training samples"""
        cursor = self._get_cursor()
        cursor.execute("SELECT COUNT(*) as count FROM training_data WHERE teacher_output IS NOT NULL")
        return cursor.fetchone()['count']

    def export_training_dataset(self, output_path: str, format: str = "jsonl"):
        """Export training data for fine-tuning"""
        import json
        from pathlib import Path

        samples = self.get_training_samples(limit=100000)
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if format == "jsonl":
            with open(output_file, 'w') as f:
                for sample in samples:
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
        user_id,  # UUID string
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
        """Create a new listing - user_id is UUID"""
        cursor = self._get_cursor()

        # user_id is UUID in listings table
        user_id_str = str(user_id) if user_id else None
        if not user_id_str:
            raise ValueError("user_id is required and must be a valid UUID")
        
        cursor.execute("""
            INSERT INTO listings (
                listing_uuid, user_id, collectible_id, title, description, price,
                cost, condition, category, item_type, attributes, photos, quantity,
                storage_location, sku, upc, status
            ) VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            listing_uuid, user_id_str, collectible_id, title, description, price,
            cost, condition, category, item_type,
            json.dumps(attributes) if attributes else None,
            json.dumps(photos),
            quantity,
            storage_location,
            sku,
            upc,
            status,
        ))

        result = cursor.fetchone()
        self.conn.commit()
        return result['id']

    def get_listing(self, listing_id: int) -> Optional[Dict]:
        """Get a listing by ID"""
        cursor = self._get_cursor()
        cursor.execute("SELECT * FROM listings WHERE id = %s", (listing_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_listing_by_uuid(self, listing_uuid: str) -> Optional[Dict]:
        """Get a listing by UUID"""
        cursor = self._get_cursor()
        cursor.execute("SELECT * FROM listings WHERE listing_uuid = %s", (listing_uuid,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_drafts(self, limit: int = 100, user_id: Optional[str] = None) -> List[Dict]:
        """Get all draft listings - user_id is UUID string"""
        cursor = self._get_cursor()
        try:
            if user_id is not None:
                user_id_str = str(user_id)
                cursor.execute("""
                    SELECT * FROM listings
                    WHERE status = 'draft' AND user_id::text = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id_str, limit))
            else:
                cursor.execute("""
                    SELECT * FROM listings
                    WHERE status = 'draft'
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting drafts: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_active_listings(self, user_id: str, limit: int = 1000) -> List[Dict]:
        """Get all active listings for a user - user_id is UUID string"""
        cursor = self._get_cursor()
        user_id_str = str(user_id)
        cursor.execute("""
            SELECT * FROM listings
            WHERE status = 'active' AND user_id::text = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id_str, limit))
        return [dict(row) for row in cursor.fetchall()]

    def update_listing_status(self, listing_id: int, status: str):
        """Update listing status"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE listings
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (status, listing_id))
        self.conn.commit()

    def delete_listing(self, listing_id: int):
        """Delete a listing and its platform listings"""
        cursor = self._get_cursor()
        cursor.execute("DELETE FROM platform_listings WHERE listing_id = %s", (listing_id,))
        cursor.execute("DELETE FROM listings WHERE id = %s", (listing_id,))
        self.conn.commit()

    def update_listing(
        self,
        listing_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[float] = None,
        cost: Optional[float] = None,
        condition: Optional[str] = None,
        category: Optional[str] = None,
        item_type: Optional[str] = None,
        attributes: Optional[Dict] = None,
        photos: Optional[List[str]] = None,
        quantity: Optional[int] = None,
        storage_location: Optional[str] = None,
        sku: Optional[str] = None,
        upc: Optional[str] = None,
        status: Optional[str] = None,
    ):
        """Update a listing with provided fields"""
        cursor = self._get_cursor()

        # Build dynamic UPDATE query based on provided parameters
        updates = []
        values = []

        if title is not None:
            updates.append("title = %s")
            values.append(title)
        if description is not None:
            updates.append("description = %s")
            values.append(description)
        if price is not None:
            updates.append("price = %s")
            values.append(price)
        if cost is not None:
            updates.append("cost = %s")
            values.append(cost)
        if condition is not None:
            updates.append("condition = %s")
            values.append(condition)
        if category is not None:
            updates.append("category = %s")
            values.append(category)
        if item_type is not None:
            updates.append("item_type = %s")
            values.append(item_type)
        if attributes is not None:
            updates.append("attributes = %s")
            values.append(json.dumps(attributes))
        if photos is not None:
            updates.append("photos = %s")
            values.append(json.dumps(photos))
        if quantity is not None:
            updates.append("quantity = %s")
            values.append(quantity)
        if storage_location is not None:
            updates.append("storage_location = %s")
            values.append(storage_location)
        if sku is not None:
            updates.append("sku = %s")
            values.append(sku)
        if upc is not None:
            updates.append("upc = %s")
            values.append(upc)
        if status is not None:
            updates.append("status = %s")
            values.append(status)

        # Always update the updated_at timestamp
        updates.append("updated_at = CURRENT_TIMESTAMP")

        # Add listing_id to values
        values.append(listing_id)

        # Execute update
        query = f"UPDATE listings SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(query, values)
        self.conn.commit()

    def get_listing_by_sku(self, sku: str) -> Optional[Dict]:
        """Get a listing by SKU"""
        cursor = self._get_cursor()
        cursor.execute("SELECT * FROM listings WHERE sku = %s LIMIT 1", (sku,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_listing_by_upc(self, upc: str) -> Optional[Dict]:
        """Get a listing by UPC"""
        cursor = self._get_cursor()
        cursor.execute("SELECT * FROM listings WHERE upc = %s LIMIT 1", (upc,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_listings_by_title(
        self,
        user_id: int,
        title_query: str,
        threshold: float = 0.8
    ) -> List[Dict]:
        """
        Search listings by title (fuzzy match)

        Args:
            user_id: User ID
            title_query: Title search query
            threshold: Similarity threshold (0.0-1.0)

        Returns:
            List of matching listings
        """
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM listings
            WHERE user_id::text = %s::text
            AND LOWER(title) LIKE LOWER(%s)
            ORDER BY created_at DESC
            LIMIT 10
        """, (str(user_id), f"%{title_query}%"))
        return [dict(row) for row in cursor.fetchall()]

    def mark_listing_sold(
        self,
        listing_id: int,
        platform: str,
        sold_price: Optional[float] = None
    ):
        """Mark a listing as sold"""
        cursor = self._get_cursor()

        cursor.execute("""
            UPDATE listings
            SET status = 'sold',
                sold_platform = %s,
                sold_date = CURRENT_TIMESTAMP,
                sold_price = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (platform, sold_price, listing_id))

        cursor.execute("""
            UPDATE platform_listings
            SET status = CASE
                WHEN platform = %s THEN 'sold'
                ELSE 'canceled'
            END,
            last_synced = CURRENT_TIMESTAMP
            WHERE listing_id = %s
        """, (platform, listing_id))

        self.conn.commit()

    # ========================================================================
    # SKU SYSTEM METHODS
    # ========================================================================

    def generate_auto_sku(self, user_id: int, prefix: str = "RR") -> str:
        """Generate an auto SKU for a user"""
        cursor = self._get_cursor()

        # Get the next SKU number for this user
        cursor.execute("""
            SELECT COUNT(*) as sku_count FROM listings
            WHERE user_id::text = %s::text AND sku LIKE %s
        """, (str(user_id), f"{prefix}%"))

        result = cursor.fetchone()
        next_number = result['sku_count'] + 1

        # Format as RR00001, RR00002, etc.
        sku = f"{prefix}{next_number:05d}"

        # Ensure uniqueness (in case of concurrent requests)
        while self.get_listing_by_sku(sku):
            next_number += 1
            sku = f"{prefix}{next_number:05d}"

        return sku

    def assign_auto_sku_if_missing(self, listing_id: int, user_id: int, prefix: str = "RR"):
        """Assign an auto-generated SKU to a listing if it doesn't have one"""
        cursor = self._get_cursor()

        # Check if listing already has a SKU
        cursor.execute("SELECT sku FROM listings WHERE id = %s", (listing_id,))
        result = cursor.fetchone()

        if result and result['sku']:
            return result['sku']  # Already has SKU

        # Generate and assign new SKU
        sku = self.generate_auto_sku(user_id, prefix)

        cursor.execute("""
            UPDATE listings SET sku = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (sku, listing_id))

        self.conn.commit()
        return sku

    def get_sku_settings(self, user_id: int) -> Dict:
        """Get SKU settings for a user (placeholder for future customization)"""
        # For now, return default settings
        return {
            'auto_generate': True,
            'prefix': 'RR',
            'pattern': '{prefix}{number:05d}'
        }

    def update_sku_settings(self, user_id: int, settings: Dict):
        """Update SKU settings for a user (placeholder for future implementation)"""
        # TODO: Store user-specific SKU settings in database
        pass

    def search_by_sku(self, user_id: int, sku_query: str) -> List[Dict]:
        """Search listings by SKU"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM listings
            WHERE user_id::text = %s::text AND sku ILIKE %s
            ORDER BY created_at DESC
        """, (str(user_id), f"%{sku_query}%"))
        return [dict(row) for row in cursor.fetchall()]

    def validate_sku_uniqueness(self, sku: str, exclude_listing_id: Optional[int] = None) -> bool:
        """Check if SKU is unique across all listings"""
        cursor = self._get_cursor()

        if exclude_listing_id:
            cursor.execute("""
                SELECT COUNT(*) as count FROM listings
                WHERE sku = %s AND id != %s
            """, (sku, exclude_listing_id))
        else:
            cursor.execute("""
                SELECT COUNT(*) as count FROM listings WHERE sku = %s
            """, (sku,))

        result = cursor.fetchone()
        return result['count'] == 0

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

        cursor.execute("""
            INSERT INTO platform_listings (
                listing_id, platform, platform_listing_id,
                platform_url, status, posted_at
            ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (listing_id, platform) DO UPDATE SET
                platform_listing_id = EXCLUDED.platform_listing_id,
                platform_url = EXCLUDED.platform_url,
                status = EXCLUDED.status,
                posted_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (listing_id, platform, platform_listing_id, platform_url, status))

        result = cursor.fetchone()
        self.conn.commit()
        return result['id']

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
            SET status = %s,
                platform_listing_id = COALESCE(%s, platform_listing_id),
                platform_url = COALESCE(%s, platform_url),
                error_message = %s,
                last_synced = CURRENT_TIMESTAMP
            WHERE listing_id = %s AND platform = %s
        """, (status, platform_listing_id, platform_url, error_message, listing_id, platform))

        self.conn.commit()

    def get_platform_listings(self, listing_id: int) -> List[Dict]:
        """Get all platform listings for a listing"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM platform_listings WHERE listing_id = %s
        """, (listing_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_active_listings_by_platform(self, platform: str) -> List[Dict]:
        """Get all active listings for a specific platform"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT l.*, pl.platform_listing_id, pl.platform_url, pl.status as platform_status
            FROM listings l
            JOIN platform_listings pl ON l.id = pl.listing_id
            WHERE pl.platform = %s AND pl.status = 'active'
        """, (platform,))
        return [dict(row) for row in cursor.fetchall()]


    def add_to_public_collectibles(self, item_type: str, data: dict, scanned_by: int) -> Optional[int]:
        """Add item to public collectibles database"""
        cursor = self._get_cursor()
        
        # Check if already exists
        if item_type == 'card':
            identifier = data.get('card_name') or data.get('player_name')
            set_name = data.get('set_name')
            card_number = data.get('card_number')
            
            cursor.execute("""
                SELECT id FROM public_collectibles 
                WHERE item_type = %s AND item_name = %s 
                AND (set_name = %s OR set_name IS NULL) 
                AND (card_number = %s OR card_number IS NULL)
            """, (item_type, identifier, set_name, card_number))
        else:
            identifier = data.get('item_name')
            franchise = data.get('franchise')
            
            cursor.execute("""
                SELECT id FROM public_collectibles 
                WHERE item_type = %s AND item_name = %s AND franchise = %s
            """, (item_type, identifier, franchise))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update scan count
            cursor.execute("""
                UPDATE public_collectibles 
                SET times_scanned = times_scanned + 1, last_updated = NOW()
                WHERE id = %s
            """, (existing['id'],))
            self.conn.commit()
            return existing['id']
        
        # Insert new
        cursor.execute("""
            INSERT INTO public_collectibles (
                item_type, item_name, franchise, brand, year,
                set_name, card_number, rarity_info, 
                authentication_markers, market_data,
                full_data, first_scanned_by, times_scanned
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            RETURNING id
        """, (
            item_type,
            identifier,
            data.get('franchise') or data.get('game_name') or data.get('sport'),
            data.get('brand'),
            data.get('year'),
            data.get('set_name'),
            data.get('card_number'),
            data.get('rarity_info') or data.get('rarity'),
            json.dumps(data.get('authentication_markers', [])),
            json.dumps({
                'estimated_value_low': data.get('estimated_value_low'),
                'estimated_value_high': data.get('estimated_value_high')
            }),
            json.dumps(data),
            scanned_by
        ))
        
        result = cursor.fetchone()
        self.conn.commit()
        return result['id']
    
    def add_to_user_collectibles(self, user_id: int, data: dict, photos: list = None, storage_location: str = None) -> Optional[int]:
        """Add collectible to user's personal collection"""
        cursor = self._get_cursor()
        
        cursor.execute("""
            INSERT INTO user_collectibles (
                user_id, item_name, franchise, brand, year,
                condition, estimated_value, storage_location,
                photos, full_data, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (
            user_id,
            data.get('item_name'),
            data.get('franchise'),
            data.get('brand'),
            data.get('year'),
            data.get('item_condition') or data.get('estimated_condition'),
            data.get('estimated_value_low'),
            storage_location,
            json.dumps(photos or []),
            json.dumps(data)
        ))
        
        result = cursor.fetchone()
        self.conn.commit()
        return result['id']

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
            VALUES (%s, %s, %s, %s, %s)
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
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (type, listing_id, platform, title, message, json.dumps(data) if data else None))
        result = cursor.fetchone()
        self.conn.commit()
        return result['id']

    def get_unread_notifications(self) -> List[Dict]:
        """Get all unread notifications"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM notifications
            WHERE is_read = FALSE
            ORDER BY created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def mark_notification_read(self, notification_id: int):
        """Mark a notification as read"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE notifications
            SET is_read = TRUE
            WHERE id = %s
        """, (notification_id,))
        self.conn.commit()

    def mark_notification_emailed(self, notification_id: int):
        """Mark a notification as emailed"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE notifications
            SET sent_email = TRUE
            WHERE id = %s
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
            VALUES (%s, %s, %s)
            RETURNING id
        """, (collectible_id, target_price, condition))
        result = cursor.fetchone()
        self.conn.commit()
        return result['id']

    def get_active_price_alerts(self) -> List[Dict]:
        """Get all active price alerts"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT pa.*, c.name as collectible_name, c.brand, c.estimated_value_avg
            FROM price_alerts pa
            JOIN collectibles c ON pa.collectible_id = c.id
            WHERE pa.is_active = TRUE
        """)
        return [dict(row) for row in cursor.fetchall()]

    # ========================================================================
    # USER AUTHENTICATION METHODS
    # ========================================================================

    def create_user(self, username: str, email: str, password_hash: str):
        """Create a new user - returns UUID"""
        import uuid
        cursor = None
        conn = None
        try:
            cursor, conn = self._get_cursor()
            user_uuid = uuid.uuid4()
            cursor.execute("""
                INSERT INTO users (id, username, email, password_hash)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (str(user_uuid), username, email, password_hash))
            result = cursor.fetchone()
            return str(result['id'])  # Return UUID as string
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                self._return_connection(conn, commit=True, error=False)

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            cursor = None
            try:
                cursor = self._get_cursor()
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                row = cursor.fetchone()
                result = dict(row) if row else None
                self._commit_read()  # Close transaction after read
                return result
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                print(f"⚠️  Database connection error in get_user_by_username (attempt {attempt + 1}/{max_retries}): {e}")
                # Force a fresh connection on retry
                if attempt < max_retries - 1:
                    try:
                        self._get_connection_from_pool()
                    except Exception as reconnect_error:
                        print(f"Failed to reconnect: {reconnect_error}")
                    time.sleep(0.5 * (attempt + 1))
                else:
                    print(f"❌ Failed to get user by username after {max_retries} attempts")
                    return None
            except Exception as e:
                print(f"Unexpected error in get_user_by_username: {e}")
                import traceback
                traceback.print_exc()
                return None
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            cursor = None
            try:
                cursor = self._get_cursor()
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                row = cursor.fetchone()
                result = dict(row) if row else None
                self._commit_read()  # Close transaction after read
                return result
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                print(f"⚠️  Database connection error in get_user_by_email (attempt {attempt + 1}/{max_retries}): {e}")
                # Force a fresh connection on retry
                if attempt < max_retries - 1:
                    try:
                        self._get_connection_from_pool()
                    except Exception as reconnect_error:
                        print(f"Failed to reconnect: {reconnect_error}")
                    time.sleep(0.5 * (attempt + 1))
                else:
                    print(f"❌ Failed to get user by email after {max_retries} attempts")
                    return None
            except Exception as e:
                print(f"Unexpected error in get_user_by_email: {e}")
                import traceback
                traceback.print_exc()
                return None
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass

    def get_user_by_id(self, user_id) -> Optional[Dict]:
        """Get user by ID (UUID) with retry logic for connection issues"""
        max_retries = 3
        for attempt in range(max_retries):
            cursor = None
            try:
                # Ensure user_id is a string UUID
                user_id_str = str(user_id) if user_id else None
                if not user_id_str:
                    return None

                cursor = self._get_cursor()
                cursor.execute("SELECT * FROM users WHERE id::text = %s", (user_id_str,))
                row = cursor.fetchone()

                if row:
                    result = dict(row)
                    # Ensure id is returned as string UUID
                    result['id'] = str(result['id'])
                    self._commit_read()  # Close transaction after read
                    return result
                self._commit_read()  # Close transaction even if no result
                return None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                print(f"⚠️  Database connection error in get_user_by_id (attempt {attempt + 1}/{max_retries}): {e}")
                # Force a fresh connection on retry
                if attempt < max_retries - 1:
                    try:
                        self._get_connection_from_pool()
                    except Exception as reconnect_error:
                        print(f"Failed to reconnect: {reconnect_error}")
                    time.sleep(0.5 * (attempt + 1))
                else:
                    print(f"❌ Failed to get user after {max_retries} attempts")
                    return None
            except (ValueError, TypeError) as e:
                print(f"Invalid user_id format: {user_id}, error: {e}")
                return None
            except Exception as e:
                print(f"Unexpected error in get_user_by_id: {e}")
                import traceback
                traceback.print_exc()
                return None
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass

    def update_last_login(self, user_id):
        """Update user's last login timestamp - user_id is UUID"""
        cursor = None
        conn = None
        try:
            cursor = self._get_cursor()
            user_id_str = str(user_id)
            cursor.execute("""
                UPDATE users
                SET last_login = CURRENT_TIMESTAMP
                WHERE id::text = %s
            """, (user_id_str,))
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                self._return_connection(conn, commit=True, error=False)

    def update_notification_email(self, user_id: int, notification_email: str):
        """Update user's notification email"""
        cursor = None
        conn = None
        try:
            cursor, conn = self._get_cursor()
            cursor.execute("""
                UPDATE users
                SET notification_email = %s
                WHERE id = %s
            """, (notification_email, user_id))
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                self._return_connection(conn, commit=True, error=False)

    # OAuth-specific methods
    def get_user_by_supabase_uid(self, supabase_uid: str) -> Optional[Dict]:
        """Get user by Supabase UID (for OAuth) - with auto-reconnect"""
        max_retries = 3
        for attempt in range(max_retries):
            cursor = None
            conn = None
            try:
                cursor = self._get_cursor()
                cursor.execute("SELECT * FROM users WHERE supabase_uid = %s", (supabase_uid,))
                row = cursor.fetchone()
                result = dict(row) if row else None
                self._commit_read()  # Close transaction after read
                return result
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Database connection error in get_user_by_supabase_uid (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(0.5 * (attempt + 1))
                    try:
                        self._get_connection_from_pool()  # Force reconnect
                    except:
                        pass
                else:
                    print(f"❌ Failed to get user by supabase_uid after {max_retries} attempts: {e}")
                    return None
            except Exception as e:
                print(f"Unexpected error in get_user_by_supabase_uid: {e}")
                return None
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
                if conn:
                    self._return_connection(conn, commit=False, error=False)

    def create_oauth_user(self, username: str, email: str, supabase_uid: str, oauth_provider: str) -> str:
        """Create a new OAuth user (no password) - returns UUID string - with auto-reconnect"""
        import uuid
        max_retries = 3
        for attempt in range(max_retries):
            cursor = None
            conn = None
            try:
                cursor = self._get_cursor()
                user_uuid = uuid.uuid4()
                cursor.execute("""
                    INSERT INTO users (id, username, email, supabase_uid, oauth_provider, email_verified)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    RETURNING id
                """, (str(user_uuid), username, email, supabase_uid, oauth_provider))
                result = cursor.fetchone()
                self.conn.commit()  # Commit the transaction
                return str(result['id'])
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Database connection error in create_oauth_user (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(0.5 * (attempt + 1))
                    try:
                        self._get_connection_from_pool()  # Force reconnect
                    except:
                        pass
                else:
                    print(f"❌ Failed to create OAuth user after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                print(f"Unexpected error in create_oauth_user: {e}")
                if self.conn:
                    try:
                        self.conn.rollback()
                    except:
                        pass
                raise
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
                if conn:
                    self._return_connection(conn, commit=True, error=False)

    def link_supabase_account(self, user_id: str, supabase_uid: str, oauth_provider: str):
        """Link an existing user account to Supabase OAuth - user_id is UUID"""
        cursor = None
        conn = None
        try:
            cursor = self._get_cursor()
            user_id_str = str(user_id)
            cursor.execute("""
                UPDATE users
                SET supabase_uid = %s,
                    oauth_provider = %s,
                    email_verified = TRUE
                WHERE id::text = %s
            """, (supabase_uid, oauth_provider, user_id_str))
            self.conn.commit()  # Commit the transaction
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                self._return_connection(conn, commit=True, error=False)

    # ========================================================================
    # MARKETPLACE CREDENTIALS METHODS
    # ========================================================================

    def save_marketplace_credentials(self, user_id, platform: str, username: str, password: str):
        """Save or update marketplace credentials - user_id is UUID"""
        cursor = self._get_cursor()
        user_id_str = str(user_id)

        cursor.execute("""
            INSERT INTO marketplace_credentials
            (user_id, platform, username, password, updated_at)
            VALUES (%s::uuid, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, platform) DO UPDATE SET
                username = EXCLUDED.username,
                password = EXCLUDED.password,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id_str, platform, username, password))

        self.conn.commit()

    def get_marketplace_credentials(self, user_id: str, platform: str) -> Optional[Dict]:
        """Get marketplace credentials for a specific platform - user_id is UUID"""
        cursor = None
        conn = None
        try:
            cursor, conn = self._get_cursor()
            user_id_str = str(user_id)
            cursor.execute("""
                SELECT * FROM marketplace_credentials
                WHERE user_id::text = %s AND platform = %s
            """, (user_id_str, platform))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                self._return_connection(conn, commit=False, error=False)

    def get_all_marketplace_credentials(self, user_id: str) -> List[Dict]:
        """Get all marketplace credentials for a user - user_id is UUID"""
        cursor = None
        conn = None
        try:
            cursor, conn = self._get_cursor()
            user_id_str = str(user_id)
            cursor.execute("""
                SELECT * FROM marketplace_credentials
                WHERE user_id::text = %s
                ORDER BY platform
            """, (user_id_str,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                self._return_connection(conn, commit=False, error=False)

    def delete_marketplace_credentials(self, user_id: str, platform: str):
        """Delete marketplace credentials for a platform - user_id is UUID"""
        cursor = self._get_cursor()
        user_id_str = str(user_id)
        cursor.execute("""
            DELETE FROM marketplace_credentials
            WHERE user_id::text = %s AND platform = %s
        """, (user_id_str, platform))
        self.conn.commit()

    # ========================================================================
    # ACTIVITY LOG METHODS
    # ========================================================================

    def log_activity(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log a user activity - user_id is UUID string"""
        cursor = None
        conn = None
        try:
            cursor = self._get_cursor()
            user_id_uuid = None
            if user_id:
                user_id_uuid = str(user_id)
            cursor.execute("""
                INSERT INTO activity_logs (
                    user_id, action, resource_type, resource_id, details,
                    ip_address, user_agent
                ) VALUES (%s::uuid, %s, %s, %s, %s, %s, %s)
            """, (
                user_id_uuid,
                action, resource_type, resource_id,
                json.dumps(details) if details else None,
                ip_address, user_agent
            ))
            self.conn.commit()  # Commit write operation
        except Exception as e:
            # Silently skip activity logging if it fails
            print(f"⚠️  Activity logging skipped: {e}")
            try:
                if self.conn and not self.conn.closed:
                    self.conn.rollback()
            except:
                pass
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                self._return_connection(conn, commit=True, error=False)

    def get_activity_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get activity logs with optional filters - user_id is UUID"""
        cursor = self._get_cursor()
        sql = "SELECT * FROM activity_logs WHERE 1=1"
        params = []

        if user_id is not None:
            sql += " AND user_id::text = %s"
            params.append(str(user_id))

        if action:
            sql += " AND action = %s"
            params.append(action)

        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_user_activity_count(self, user_id: int) -> int:
        """Get total activity count for a user"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM activity_logs WHERE user_id::text = %s::text
        """, (str(user_id),))
        return cursor.fetchone()['count']

    # ========================================================================
    # ADMIN METHODS
    # ========================================================================

    def get_all_users(self, include_inactive: bool = False) -> List[Dict]:
        """Get all users (admin function)"""
        cursor = self._get_cursor()
        if include_inactive:
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM users WHERE is_active = TRUE ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def toggle_user_admin(self, user_id: int) -> bool:
        """Toggle admin status for a user"""
        cursor = self._get_cursor()
        cursor.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False

        new_status = not row['is_admin']
        cursor.execute("UPDATE users SET is_admin = %s WHERE id = %s", (new_status, user_id))
        self.conn.commit()
        return True

    def toggle_user_active(self, user_id: int) -> bool:
        """Toggle active status for a user"""
        cursor = self._get_cursor()
        cursor.execute("SELECT is_active FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False

        new_status = not row['is_active']
        cursor.execute("UPDATE users SET is_active = %s WHERE id = %s", (new_status, user_id))
        self.conn.commit()
        return True

    def delete_user(self, user_id: int):
        """Delete a user and all their data"""
        cursor = self._get_cursor()

        cursor.execute("DELETE FROM marketplace_credentials WHERE user_id::text = %s::text", (str(user_id),))
        cursor.execute("DELETE FROM listings WHERE user_id::text = %s::text", (str(user_id),))
        cursor.execute("DELETE FROM activity_logs WHERE user_id::text = %s::text", (str(user_id),))
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))

        self.conn.commit()

    def get_system_stats(self) -> Dict:
        """Get system statistics"""
        cursor = self._get_cursor()

        stats = {}

        cursor.execute("SELECT COUNT(*) as count FROM users")
        stats['total_users'] = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = TRUE")
        stats['admin_users'] = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_active = TRUE")
        stats['active_users'] = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM listings")
        stats['total_listings'] = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM listings WHERE status = 'draft'")
        stats['draft_listings'] = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM listings WHERE status = 'sold'")
        stats['sold_listings'] = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM activity_logs WHERE created_at > NOW() - INTERVAL '7 days'")
        stats['activity_last_7_days'] = cursor.fetchone()['count']

        return stats

    # ========================================================================
    # EMAIL TOKEN METHODS
    # ========================================================================

    def set_verification_token(self, user_id: int, token: str):
        """Set email verification token"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE users
            SET verification_token = %s
            WHERE id = %s
        """, (token, user_id))
        self.conn.commit()

    def verify_email(self, token: str) -> bool:
        """Verify email with token"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE users
            SET email_verified = TRUE, verification_token = NULL
            WHERE verification_token = %s
        """, (token,))
        self.conn.commit()
        return cursor.rowcount > 0

    def set_reset_token(self, user_id: int, token: str, expiry_hours: int = 24):
        """Set password reset token"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE users
            SET reset_token = %s,
                reset_token_expiry = NOW() + INTERVAL '%s hours'
            WHERE id = %s
        """, (token, expiry_hours, user_id))
        self.conn.commit()

    def verify_reset_token(self, token: str) -> Optional[Dict]:
        """Verify reset token and return user if valid"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM users
            WHERE reset_token = %s
            AND reset_token_expiry > NOW()
        """, (token,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_password(self, user_id: int, new_password_hash: str):
        """Update user password and clear reset token"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE users
            SET password_hash = %s,
                reset_token = NULL,
                reset_token_expiry = NULL
            WHERE id = %s
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
        """Add platform activity"""
        cursor = self._get_cursor()
        cursor.execute("""
            INSERT INTO platform_activity (
                user_id, platform, activity_type, platform_listing_id,
                listing_id, title, buyer_username, message_text,
                sold_price, activity_date, raw_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id, platform, activity_type, platform_listing_id,
            listing_id, title, buyer_username, message_text,
            sold_price, activity_date or datetime.now().isoformat(), raw_data
        ))
        result = cursor.fetchone()
        self.conn.commit()
        return result['id']

    def get_platform_activity(
        self,
        user_id: int,
        limit: int = 50,
        unread_only: bool = False,
        activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get platform activity for a user"""
        cursor = self._get_cursor()

        query = """
            SELECT * FROM platform_activity
            WHERE user_id::text = %s::text
        """
        params = [user_id]

        if unread_only:
            query += " AND is_read = FALSE"

        if activity_type:
            query += " AND activity_type = %s"
            params.append(activity_type)

        query += " ORDER BY activity_date DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def mark_activity_read(self, activity_id: int):
        """Mark platform activity as read"""
        cursor = self._get_cursor()
        cursor.execute("""
            UPDATE platform_activity
            SET is_read = TRUE
            WHERE id = %s
        """, (activity_id,))
        self.conn.commit()

    def sync_sold_activity_to_inventory(self, activity_id: int):
        """Sync sold activity to inventory"""
        cursor = self._get_cursor()

        cursor.execute("SELECT * FROM platform_activity WHERE id = %s", (activity_id,))
        activity = cursor.fetchone()

        if not activity or activity['activity_type'] != 'sold':
            return False

        listing_id = activity['listing_id']
        if not listing_id:
            return False

        cursor.execute("""
            UPDATE listings
            SET status = 'sold',
                sold_platform = %s,
                sold_date = %s,
                sold_price = %s
            WHERE id = %s
        """, (
            activity['platform'],
            activity['activity_date'],
            activity['sold_price'],
            listing_id
        ))

        cursor.execute("""
            UPDATE platform_activity
            SET is_synced_to_inventory = TRUE
            WHERE id = %s
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
        """Check if item already exists on a platform"""
        cursor = self._get_cursor()

        if upc or sku:
            query = """
                SELECT l.*
                FROM listings l
                JOIN platform_listings pl ON l.id = pl.listing_id
                WHERE l.user_id::text = %s::text
                AND pl.platform = %s
                AND pl.status IN ('active', 'pending')
                AND (l.upc = %s OR l.sku = %s)
                LIMIT 1
            """
            cursor.execute(query, (str(user_id), platform, upc or '', sku or ''))
            row = cursor.fetchone()
            if row:
                return dict(row)

        query = """
            SELECT l.*, pl.platform_listing_id, pl.status as platform_status
            FROM listings l
            JOIN platform_listings pl ON l.id = pl.listing_id
            WHERE l.user_id::text = %s::text
            AND pl.platform = %s
            AND pl.status IN ('active', 'pending')
            AND LOWER(l.title) LIKE LOWER(%s)
        """
        search_pattern = f"%{title[:50]}%"
        cursor.execute(query, (str(user_id), platform, search_pattern))
        row = cursor.fetchone()

        return dict(row) if row else None

    # ========================================================================
    # STORAGE SYSTEM METHODS
    # ========================================================================

    def create_storage_bin(
        self,
        user_id: int,
        bin_name: str,
        bin_type: str,
        description: Optional[str] = None
    ) -> int:
        """Create a new storage bin"""
        cursor = self._get_cursor()
        cursor.execute("""
            INSERT INTO storage_bins (user_id, bin_name, bin_type, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (user_id, bin_name, bin_type, description))
        result = cursor.fetchone()
        self.conn.commit()
        return result['id']

    def get_storage_bins(self, user_id: int, bin_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all storage bins for a user"""
        cursor = self._get_cursor()

        if bin_type:
            cursor.execute("""
                SELECT * FROM storage_bins
                WHERE user_id::text = %s::text AND bin_type = %s
                ORDER BY bin_name
            """, (user_id, bin_type))
        else:
            cursor.execute("""
                SELECT * FROM storage_bins
                WHERE user_id::text = %s::text
                ORDER BY bin_type, bin_name
            """, (str(user_id),))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def create_storage_section(
        self,
        bin_id: int,
        section_name: str,
        capacity: Optional[int] = None
    ) -> int:
        """Create a section within a bin"""
        cursor = self._get_cursor()
        cursor.execute("""
            INSERT INTO storage_sections (bin_id, section_name, capacity)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (bin_id, section_name, capacity))
        result = cursor.fetchone()
        self.conn.commit()
        return result['id']

    def get_storage_sections(self, bin_id: int) -> List[Dict[str, Any]]:
        """Get all sections for a bin"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM storage_sections
            WHERE bin_id = %s
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
        """Generate next available storage ID"""
        cursor = self._get_cursor()

        if category:
            pattern = f"{category}-{bin_name}{section_name or ''}-%"
        elif section_name:
            pattern = f"{bin_name}{section_name}-%"
        else:
            pattern = f"{bin_name}-%"

        cursor.execute("""
            SELECT storage_id FROM storage_items
            WHERE user_id::text = %s::text AND storage_id LIKE %s
            ORDER BY storage_id DESC
            LIMIT 1
        """, (user_id, pattern))

        row = cursor.fetchone()

        if row:
            last_id = row['storage_id']
            try:
                last_num = int(last_id.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

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
        """Add item to storage"""
        cursor = self._get_cursor()

        photos_json = json.dumps(photos) if photos else None

        cursor.execute("""
            INSERT INTO storage_items (
                user_id, storage_id, bin_id, section_id, item_type,
                category, title, description, quantity, photos, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id, storage_id, bin_id, section_id, item_type,
            category, title, description, quantity, photos_json, notes
        ))

        result = cursor.fetchone()

        if section_id:
            cursor.execute("""
                UPDATE storage_sections
                SET item_count = item_count + %s
                WHERE id = %s
            """, (quantity, section_id))

        self.conn.commit()
        return result['id']

    def find_storage_item(self, user_id: int, storage_id: str) -> Optional[Dict[str, Any]]:
        """Find item by storage ID"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT si.*, sb.bin_name, sb.bin_type, ss.section_name
            FROM storage_items si
            JOIN storage_bins sb ON si.bin_id = sb.id
            LEFT JOIN storage_sections ss ON si.section_id = ss.id
            WHERE si.user_id::text = %s::text AND si.storage_id = %s
        """, (str(user_id), storage_id))
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
        """Get storage items with filters"""
        cursor = self._get_cursor()

        query = """
            SELECT si.*, sb.bin_name, sb.bin_type, ss.section_name
            FROM storage_items si
            JOIN storage_bins sb ON si.bin_id = sb.id
            LEFT JOIN storage_sections ss ON si.section_id = ss.id
            WHERE si.user_id::text = %s::text
        """
        params = [str(user_id)]

        if bin_id:
            query += " AND si.bin_id = %s"
            params.append(bin_id)

        if section_id:
            query += " AND si.section_id = %s"
            params.append(section_id)

        if item_type:
            query += " AND si.item_type = %s"
            params.append(item_type)

        query += " ORDER BY si.created_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_storage_map(self, user_id: int) -> Dict[str, Any]:
        """Get complete storage map"""
        cursor = self._get_cursor()

        cursor.execute("""
            SELECT
                sb.*,
                COUNT(DISTINCT ss.id) as section_count
            FROM storage_bins sb
            LEFT JOIN storage_sections ss ON sb.id = ss.bin_id
            WHERE sb.user_id::text = %s::text
            GROUP BY sb.id
            ORDER BY sb.bin_type, sb.bin_name
        """, (str(user_id),))

        bins = [dict(row) for row in cursor.fetchall()]

        clothing_bins = [b for b in bins if b.get('bin_type') == 'clothing']
        card_bins = [b for b in bins if b.get('bin_type') == 'cards']

        for bin_data in bins:
            sections = self.get_storage_sections(bin_data['id'])
            bin_data['sections'] = sections

        cursor.execute("""
            SELECT COUNT(*) as total
            FROM storage_items
            WHERE user_id::text = %s::text
        """, (str(user_id),))

        result = cursor.fetchone()
        total_items = result['total'] if result else 0

        return {
            'clothing_bins': clothing_bins,
            'card_bins': card_bins,
            'total_items': total_items
        }

    def _seed_data(self):
        """Seed initial data - creates admin and tier 3 user if they don't exist"""
        from werkzeug.security import generate_password_hash
        
        cursor = self._get_cursor()
        
        # Admin user
        cursor.execute("SELECT id FROM users WHERE username = %s", ("lyakGodzilla",))
        if not cursor.fetchone():
            admin_password_hash = generate_password_hash("<3love")
            cursor.execute("""
                INSERT INTO users (
                    username, email, password_hash, is_admin, is_active, 
                    tier, email_verified
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                "lyakGodzilla",
                "little.cee.zers@gmail.com",
                admin_password_hash,
                True,  # is_admin
                True,  # is_active
                "ADMIN",  # tier
                True   # email_verified
            ))
            self.conn.commit()
            print("✅ Admin user (lyakGodzilla) created")
        
        # Tier 3 user (friend)
        cursor.execute("SELECT id FROM users WHERE username = %s", ("ResellRage",))
        if not cursor.fetchone():
            tier3_password_hash = generate_password_hash("Kade031109!")
            cursor.execute("""
                INSERT INTO users (
                    username, email, password_hash, is_admin, is_active, 
                    tier, email_verified
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                "ResellRage",
                "resellrage@example.com",
                tier3_password_hash,
                False,  # is_admin
                True,   # is_active
                "TIER_3",  # tier
                True    # email_verified
            ))
            self.conn.commit()
            print("✅ Tier 3 user (ResellRage) created")

    def run_migrations(self):
        """
        Run database migrations manually.
        Call this once to set up tables, not on every startup.
        Usage: db.run_migrations()
        """
        print("🔧 Running database migrations...")
        self._create_tables()
        self._seed_data()
        print("✅ Migrations complete!")

    def close(self):
        """Close database connection"""
        self.conn.close()


# ============================================================================
# TIER-BASED FEATURE PERMISSIONS
# ============================================================================

TIER_FEATURES = {
    "ADMIN": {
        "auto_lister": True,
        "ai_generation": True,
        "drafts": True,
        "csv_export": True,
        "storage_organizing": True,
        "collectible_search": True,
        "multiplatform_notifications": True,
    },
    "TIER_3": {
        "auto_lister": True,
        "ai_generation": True,
        "drafts": True,
        "csv_export": True,
        "storage_organizing": False,
        "collectible_search": False,
        "multiplatform_notifications": False,
    },
    "TIER_2": {
        "auto_lister": True,
        "ai_generation": True,
        "drafts": True,
        "csv_export": True,
        "storage_organizing": True,
        "collectible_search": False,
        "multiplatform_notifications": False,
    },
    "FREE": {
        "auto_lister": True,
        "ai_generation": True,
        "drafts": True,
        "csv_export": True,
        "storage_organizing": False,
        "collectible_search": False,
        "multiplatform_notifications": False,
    }
}

def can_access_feature(user_tier: str, feature: str) -> bool:
    """Check if user tier has access to a feature"""
    tier_perms = TIER_FEATURES.get(user_tier, TIER_FEATURES["FREE"])
    return tier_perms.get(feature, False)


# Singleton instance
_db_instance = None

def get_db() -> Database:
    """Get database singleton instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance



