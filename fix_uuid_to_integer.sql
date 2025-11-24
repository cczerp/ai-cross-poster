-- Fix all user_id columns - convert from UUID back to INTEGER
-- Run this entire script in Supabase SQL Editor

-- 1. Drop all existing RLS policies that might be using auth.uid()
DROP POLICY IF EXISTS "Service role has full access" ON activity_logs;
DROP POLICY IF EXISTS "Service role has full access" ON users;
DROP POLICY IF EXISTS "Service role has full access" ON marketplace_credentials;
DROP POLICY IF EXISTS "Service role has full access" ON listings;
DROP POLICY IF EXISTS "Service role has full access" ON training_data;
DROP POLICY IF EXISTS "Service role has full access" ON platform_activity;
DROP POLICY IF EXISTS "Service role has full access" ON storage_bins;
DROP POLICY IF EXISTS "Service role has full access" ON storage_items;
DROP POLICY IF EXISTS "Service role has full access" ON card_collections;
DROP POLICY IF EXISTS "Service role has full access" ON card_organization_presets;
DROP POLICY IF EXISTS "Service role has full access" ON card_custom_categories;

-- 2. Convert user_id columns from UUID to INTEGER
-- Activity logs
ALTER TABLE activity_logs ALTER COLUMN user_id DROP DEFAULT;
ALTER TABLE activity_logs ALTER COLUMN user_id TYPE INTEGER USING NULL;

-- Marketplace credentials (if changed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'marketplace_credentials'
        AND column_name = 'user_id'
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE marketplace_credentials ALTER COLUMN user_id TYPE INTEGER USING NULL;
    END IF;
END $$;

-- Listings (if changed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'listings'
        AND column_name = 'user_id'
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE listings ALTER COLUMN user_id TYPE INTEGER USING NULL;
    END IF;
END $$;

-- Training data (if changed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'training_data'
        AND column_name = 'user_id'
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE training_data ALTER COLUMN user_id TYPE INTEGER USING NULL;
    END IF;
END $$;

-- Platform activity (if changed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'platform_activity'
        AND column_name = 'user_id'
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE platform_activity ALTER COLUMN user_id TYPE INTEGER USING NULL;
    END IF;
END $$;

-- Storage bins (if changed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'storage_bins'
        AND column_name = 'user_id'
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE storage_bins ALTER COLUMN user_id TYPE INTEGER USING NULL;
    END IF;
END $$;

-- Storage items (if changed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'storage_items'
        AND column_name = 'user_id'
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE storage_items ALTER COLUMN user_id TYPE INTEGER USING NULL;
    END IF;
END $$;

-- Card collections (if changed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'card_collections'
        AND column_name = 'user_id'
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE card_collections ALTER COLUMN user_id TYPE INTEGER USING NULL;
    END IF;
END $$;

-- Card organization presets (if changed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'card_organization_presets'
        AND column_name = 'user_id'
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE card_organization_presets ALTER COLUMN user_id TYPE INTEGER USING NULL;
    END IF;
END $$;

-- Card custom categories (if changed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'card_custom_categories'
        AND column_name = 'user_id'
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE card_custom_categories ALTER COLUMN user_id TYPE INTEGER USING NULL;
    END IF;
END $$;

-- 3. Re-enable RLS with permissive policies
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for service role" ON activity_logs FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE marketplace_credentials ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for service role" ON marketplace_credentials FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for service role" ON listings FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE training_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for service role" ON training_data FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE platform_activity ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for service role" ON platform_activity FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE storage_bins ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for service role" ON storage_bins FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE storage_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for service role" ON storage_items FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE card_collections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for service role" ON card_collections FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE card_organization_presets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for service role" ON card_organization_presets FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE card_custom_categories ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for service role" ON card_custom_categories FOR ALL USING (true) WITH CHECK (true);

-- 4. Verify fix
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE column_name = 'user_id'
AND table_schema = 'public'
ORDER BY table_name;
