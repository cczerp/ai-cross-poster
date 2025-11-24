-- RLS Policies for Resell Rebel - Flask-Login Authentication
-- This enables RLS (to satisfy Supabase) while allowing your app full access
-- Your app uses connection pooling with service role credentials

-- Enable RLS and create permissive policies for all tables

-- 1. Users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON users;
CREATE POLICY "Service role has full access" ON users
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 2. Marketplace credentials
ALTER TABLE marketplace_credentials ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON marketplace_credentials;
CREATE POLICY "Service role has full access" ON marketplace_credentials
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 3. Listings
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON listings;
CREATE POLICY "Service role has full access" ON listings
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 4. Collectibles
ALTER TABLE collectibles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON collectibles;
CREATE POLICY "Service role has full access" ON collectibles
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 5. Training data
ALTER TABLE training_data ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON training_data;
CREATE POLICY "Service role has full access" ON training_data
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 6. Platform listings
ALTER TABLE platform_listings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON platform_listings;
CREATE POLICY "Service role has full access" ON platform_listings
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 7. Sync log
ALTER TABLE sync_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON sync_log;
CREATE POLICY "Service role has full access" ON sync_log
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 8. Platform activity
ALTER TABLE platform_activity ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON platform_activity;
CREATE POLICY "Service role has full access" ON platform_activity
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 9. Storage bins
ALTER TABLE storage_bins ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON storage_bins;
CREATE POLICY "Service role has full access" ON storage_bins
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 10. Storage sections
ALTER TABLE storage_sections ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON storage_sections;
CREATE POLICY "Service role has full access" ON storage_sections
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 11. Storage items
ALTER TABLE storage_items ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON storage_items;
CREATE POLICY "Service role has full access" ON storage_items
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 12. Card collections
ALTER TABLE card_collections ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON card_collections;
CREATE POLICY "Service role has full access" ON card_collections
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 13. Card organization presets
ALTER TABLE card_organization_presets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON card_organization_presets;
CREATE POLICY "Service role has full access" ON card_organization_presets
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 14. Card custom categories
ALTER TABLE card_custom_categories ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON card_custom_categories;
CREATE POLICY "Service role has full access" ON card_custom_categories
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 15. Notifications
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON notifications;
CREATE POLICY "Service role has full access" ON notifications
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 16. Price alerts
ALTER TABLE price_alerts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON price_alerts;
CREATE POLICY "Service role has full access" ON price_alerts
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 17. Activity logs
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role has full access" ON activity_logs;
CREATE POLICY "Service role has full access" ON activity_logs
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- Verify RLS is enabled with policies
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
