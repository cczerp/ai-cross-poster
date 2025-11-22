#!/usr/bin/env python3
"""
Database Verification Script
Checks Supabase connection and verifies tables exist
"""

import os
import sys
from src.database.db import Database

def verify_database():
    """Verify database connection and tables"""

    print("=" * 60)
    print("DATABASE VERIFICATION SCRIPT")
    print("=" * 60)
    print()

    # Check DATABASE_URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print()
        print("Please set DATABASE_URL to your Supabase connection string:")
        print("export DATABASE_URL='postgresql://user:password@host:5432/database'")
        sys.exit(1)

    # Mask password in display
    masked_url = db_url
    if '@' in masked_url:
        parts = masked_url.split('@')
        if ':' in parts[0]:
            user_pass = parts[0].split('//')[-1]
            user = user_pass.split(':')[0]
            masked_url = masked_url.replace(user_pass, f"{user}:****")

    print(f"✓ DATABASE_URL is set: {masked_url}")
    print()

    try:
        # Initialize database (this will create tables if they don't exist)
        print("Connecting to database...")
        db = Database()
        print("✓ Connected to database successfully!")
        print()

        # Verify tables exist
        print("Checking tables...")
        cursor = db._get_cursor()

        expected_tables = [
            'users',
            'marketplace_credentials',
            'collectibles',
            'listings',
            'training_data',
            'platform_listings',
            'sync_log',
            'platform_activity',
            'storage_bins',
            'storage_sections',
            'storage_items'
        ]

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        existing_tables = [row['table_name'] for row in cursor.fetchall()]

        print(f"Found {len(existing_tables)} tables in database:")
        for table in existing_tables:
            status = "✓" if table in expected_tables else "?"
            print(f"  {status} {table}")

        print()

        missing_tables = [t for t in expected_tables if t not in existing_tables]
        if missing_tables:
            print(f"⚠️  WARNING: Missing {len(missing_tables)} expected tables:")
            for table in missing_tables:
                print(f"  ❌ {table}")
            print()
        else:
            print("✓ All expected tables exist!")
            print()

        # Check listings table structure
        print("Checking 'listings' table structure...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'listings'
            ORDER BY ordinal_position
        """)

        columns = cursor.fetchall()
        if columns:
            print(f"  Found {len(columns)} columns:")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                print(f"    - {col['column_name']}: {col['data_type']} ({nullable})")
            print()
        else:
            print("  ❌ Table 'listings' not found or has no columns!")
            print()

        # Count existing data
        print("Checking existing data...")

        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()['count']
        print(f"  Users: {user_count}")

        cursor.execute("SELECT COUNT(*) as count FROM listings")
        listing_count = cursor.fetchone()['count']
        print(f"  Listings (all): {listing_count}")

        cursor.execute("SELECT COUNT(*) as count FROM listings WHERE status = 'draft'")
        draft_count = cursor.fetchone()['count']
        print(f"  Drafts: {draft_count}")

        cursor.execute("SELECT COUNT(*) as count FROM listings WHERE status = 'active'")
        active_count = cursor.fetchone()['count']
        print(f"  Active listings: {active_count}")

        print()

        # Show recent drafts
        if draft_count > 0:
            print("Recent drafts:")
            cursor.execute("""
                SELECT id, title, price,
                       CASE
                           WHEN photos IS NOT NULL THEN
                               CASE
                                   WHEN photos::text LIKE '[%' THEN
                                       jsonb_array_length(photos::jsonb)
                                   ELSE 0
                               END
                           ELSE 0
                       END as photo_count,
                       created_at
                FROM listings
                WHERE status = 'draft'
                ORDER BY created_at DESC
                LIMIT 5
            """)

            for row in cursor.fetchall():
                print(f"  - ID {row['id']}: {row['title']} (${row['price']}) - {row['photo_count']} photos - {row['created_at']}")
            print()

        print("=" * 60)
        print("✓ DATABASE VERIFICATION COMPLETE")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Check your Supabase dashboard to see the tables")
        print("2. Try creating a draft in the app")
        print("3. Refresh your Supabase dashboard to see the new data")
        print()

    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    verify_database()
