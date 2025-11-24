-- Fix user_id type mismatch: Convert UUID columns to INTEGER
-- Run this on your production database to fix the type mismatch

BEGIN;

-- Convert listings.user_id from UUID to INTEGER
ALTER TABLE listings
ALTER COLUMN user_id TYPE INTEGER USING user_id::text::integer;

-- Convert marketplace_credentials.user_id from UUID to INTEGER
ALTER TABLE marketplace_credentials
ALTER COLUMN user_id TYPE INTEGER USING user_id::text::integer;

-- Convert activity_logs.user_id from UUID to INTEGER
ALTER TABLE activity_logs
ALTER COLUMN user_id TYPE INTEGER USING user_id::text::integer;

-- Convert drafts.user_id from UUID to INTEGER
ALTER TABLE drafts
ALTER COLUMN user_id TYPE INTEGER USING user_id::text::integer;

-- Convert storage_bins.user_id from UUID to INTEGER
ALTER TABLE storage_bins
ALTER COLUMN user_id TYPE INTEGER USING user_id::text::integer;

-- Convert storage_items.user_id from UUID to INTEGER
ALTER TABLE storage_items
ALTER COLUMN user_id TYPE INTEGER USING user_id::text::integer;

-- Convert card_collections.user_id from UUID to INTEGER (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'card_collections'
               AND column_name = 'user_id') THEN
        ALTER TABLE card_collections
        ALTER COLUMN user_id TYPE INTEGER USING user_id::text::integer;
    END IF;
END $$;

COMMIT;

-- Verify the changes
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE column_name = 'user_id'
  AND table_schema = 'public'
ORDER BY table_name;
