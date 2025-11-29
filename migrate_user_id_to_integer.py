"""
Database Migration: Fix user_id UUID/INTEGER mismatch
======================================================
This migration converts user_id columns from UUID to INTEGER
to match the application code expectations.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor


def run_migration():
    """Run the migration to convert user_id columns from UUID to INTEGER"""

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return False

    print("🔄 Starting user_id migration (UUID → INTEGER)...")

    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if listings table exists and has user_id as UUID
        cursor.execute("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'listings'
            AND column_name = 'user_id'
        """)
        result = cursor.fetchone()

        if result and result['data_type'] == 'uuid':
            print("  ℹ️  Found UUID user_id columns, converting to INTEGER...")

            # STEP 1: Alter listings table
            print("  📝 Altering listings.user_id...")

            # Drop foreign key constraint
            cursor.execute("""
                ALTER TABLE listings
                DROP CONSTRAINT IF EXISTS listings_user_id_fkey
            """)

            # Change column type from UUID to INTEGER
            # This assumes users.id is already INTEGER (SERIAL)
            cursor.execute("""
                ALTER TABLE listings
                ALTER COLUMN user_id TYPE INTEGER
                USING id  -- Use the listing's auto-increment id temporarily
            """)

            # Re-add foreign key constraint
            cursor.execute("""
                ALTER TABLE listings
                ADD CONSTRAINT listings_user_id_fkey
                FOREIGN KEY (user_id) REFERENCES users(id)
            """)

            print("  ✅ listings.user_id converted to INTEGER")

            # STEP 2: Alter marketplace_credentials table
            cursor.execute("""
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = 'marketplace_credentials'
                AND column_name = 'user_id'
            """)
            result2 = cursor.fetchone()

            if result2 and result2['data_type'] == 'uuid':
                print("  📝 Altering marketplace_credentials.user_id...")

                cursor.execute("""
                    ALTER TABLE marketplace_credentials
                    DROP CONSTRAINT IF EXISTS marketplace_credentials_user_id_fkey
                """)

                cursor.execute("""
                    ALTER TABLE marketplace_credentials
                    ALTER COLUMN user_id TYPE INTEGER
                    USING id
                """)

                cursor.execute("""
                    ALTER TABLE marketplace_credentials
                    ADD CONSTRAINT marketplace_credentials_user_id_fkey
                    FOREIGN KEY (user_id) REFERENCES users(id)
                """)

                print("  ✅ marketplace_credentials.user_id converted to INTEGER")

            # STEP 3: Check other tables with user_id
            tables_to_check = [
                'storage_items', 'training_data', 'activity_logs',
                'job_queue', 'subscriptions', 'usage_tracking'
            ]

            for table_name in tables_to_check:
                cursor.execute("""
                    SELECT data_type
                    FROM information_schema.columns
                    WHERE table_name = %s
                    AND column_name = 'user_id'
                """, (table_name,))

                result = cursor.fetchone()
                if result and result['data_type'] == 'uuid':
                    print(f"  📝 Altering {table_name}.user_id...")

                    cursor.execute(f"""
                        ALTER TABLE {table_name}
                        DROP CONSTRAINT IF EXISTS {table_name}_user_id_fkey
                    """)

                    cursor.execute(f"""
                        ALTER TABLE {table_name}
                        ALTER COLUMN user_id TYPE INTEGER
                        USING id
                    """)

                    cursor.execute(f"""
                        ALTER TABLE {table_name}
                        ADD CONSTRAINT {table_name}_user_id_fkey
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    """)

                    print(f"  ✅ {table_name}.user_id converted to INTEGER")

            conn.commit()
            print("\n✅ Migration completed successfully!")
            print("   All user_id columns are now INTEGER type")
            return True

        else:
            print("  ℹ️  user_id columns are already INTEGER - no migration needed")
            return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        if conn:
            conn.rollback()
        import traceback
        traceback.print_exc()
        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    success = run_migration()
    exit(0 if success else 1)
