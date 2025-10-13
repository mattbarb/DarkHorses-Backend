-- =============================================================================
-- ADD race_name COLUMN TO ra_odds_historical
-- =============================================================================
-- This migration adds the race_name column to match ra_odds_live structure
-- The historical fetcher already captures race_name from the API, but the
-- column was missing from the table schema.
--
-- After running this, the historical worker will automatically populate
-- race_name for all new records.
-- =============================================================================

-- STEP 1: Add race_name column (nullable to allow existing records)
ALTER TABLE ra_odds_historical
ADD COLUMN race_name TEXT;

-- STEP 2: Create index for race name searches
CREATE INDEX idx_ra_odds_historical_race_name
ON ra_odds_historical (race_name);

-- STEP 3: Add comment
COMMENT ON COLUMN ra_odds_historical.race_name IS
'Official race name (e.g., "THE RAY HAWTHORNE MEMORIAL AMATEUR").
Captured from Racing API results endpoint starting from this migration.';

-- STEP 4: Verify the column was added
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'ra_odds_historical'
AND column_name = 'race_name';

-- STEP 5: Check current data
SELECT
    COUNT(*) as total_records,
    COUNT(race_name) as records_with_race_name,
    COUNT(*) - COUNT(race_name) as records_missing_race_name
FROM ra_odds_historical;

-- =============================================================================
-- DEPLOYMENT NOTES:
-- =============================================================================
-- 1. Run this migration in Supabase SQL Editor
--
-- 2. Existing records will have NULL race_name (backfill required)
--
-- 3. New records will automatically get race_name populated by the worker
--
-- 4. To backfill existing records, use the backfill script
--    (see backfill_race_names.py)
--
-- 5. This matches the ra_odds_live table structure which already has race_name
-- =============================================================================
