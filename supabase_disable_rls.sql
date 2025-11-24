-- Disable RLS on all tables for Resell Rebel app
-- This allows your app to access all tables without RLS restrictions
-- Run this in Supabase SQL Editor

-- Disable RLS on all main tables
ALTER TABLE IF EXISTS users DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS listings DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS drafts DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS photos DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS platforms DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS notifications DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS storage_locations DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS storage_items DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS cards DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS card_collections DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS password_reset_tokens DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS activity_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS sessions DISABLE ROW LEVEL SECURITY;

-- If you have any other tables, add them here:
-- ALTER TABLE IF EXISTS your_table_name DISABLE ROW LEVEL SECURITY;

-- Verify RLS is disabled
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
