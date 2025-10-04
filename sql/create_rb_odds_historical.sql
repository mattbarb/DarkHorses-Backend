-- =============================================================================
-- CREATE CLEAN rb_odds_historical TABLE
-- =============================================================================
-- This script creates a fresh rb_odds_historical table from scratch
--
-- IMPORTANT: The old problematic table should be renamed to rb_odds_historical_backup
-- before running this script.
--
-- Design Principles:
-- - ONLY racing_bet_data_id, created_at, updated_at are NOT NULL
-- - ALL other fields are nullable (maximum flexibility)
-- - NO foreign keys
-- - NO triggers
-- - NO check constraints
-- - NO darkhorses columns (darkhorses_jockey_id, darkhorses_race_id, etc.)
-- =============================================================================

-- STEP 1: Drop existing table if it exists (safety check)
-- Only run this if you've already backed up the old table!
-- Uncomment the next line if you're certain you want to drop:
-- DROP TABLE IF EXISTS rb_odds_historical CASCADE;

-- STEP 2: Create the new clean table
CREATE TABLE rb_odds_historical (
    -- Primary Key (BIGSERIAL = auto-incrementing big integer)
    racing_bet_data_id BIGSERIAL PRIMARY KEY,

    -- Race Identification Fields
    date_of_race TIMESTAMP WITH TIME ZONE,
    country VARCHAR(10),
    track TEXT,
    race_time TIME,

    -- Race Details
    going TEXT,
    race_type TEXT,
    distance TEXT,
    race_class INTEGER,
    runners_count INTEGER,

    -- Horse & Participant Information
    horse_name TEXT,
    official_rating INTEGER DEFAULT 0,
    age INTEGER,
    weight TEXT,
    jockey TEXT,
    trainer TEXT,
    headgear TEXT,
    stall_number INTEGER,

    -- Market Position
    sp_favorite_position INTEGER,

    -- Odds Data (Industry)
    industry_sp NUMERIC(10,4),

    -- Results
    finishing_position TEXT,
    winning_distance TEXT,

    -- Pre-Race Odds Analysis
    ip_min NUMERIC(10,4),
    ip_max NUMERIC(10,4),
    pre_race_min NUMERIC(10,4),
    pre_race_max NUMERIC(10,4),
    forecasted_odds NUMERIC(10,4),

    -- Returns & Performance
    sp_win_return NUMERIC(10,4),
    ew_return NUMERIC(10,4),
    place_return NUMERIC(10,4),

    -- Metadata & Tracking
    data_source TEXT,
    file_source TEXT DEFAULT 'Racing API',

    -- Timestamps (NOT NULL with defaults)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    match_timestamp TIMESTAMP WITH TIME ZONE
);

-- STEP 3: Create indexes for query performance
-- These indexes optimize common query patterns

-- Index for date-based queries
CREATE INDEX idx_rb_odds_historical_date_of_race
ON rb_odds_historical (date_of_race);

-- Index for track-based queries
CREATE INDEX idx_rb_odds_historical_track
ON rb_odds_historical (track);

-- Index for horse name searches
CREATE INDEX idx_rb_odds_historical_horse_name
ON rb_odds_historical (horse_name);

-- Composite index for uniqueness detection
-- This helps identify duplicate records: same date, track, time, horse
CREATE INDEX idx_rb_odds_historical_unique_combo
ON rb_odds_historical (date_of_race, track, race_time, horse_name);

-- Index for data source filtering
CREATE INDEX idx_rb_odds_historical_data_source
ON rb_odds_historical (data_source);

-- Index for created_at (useful for incremental processing)
CREATE INDEX idx_rb_odds_historical_created_at
ON rb_odds_historical (created_at);

-- STEP 4: Add table comment
COMMENT ON TABLE rb_odds_historical IS
'Historical racing results and odds data from Racing API (racecards + results combined).
Contains race results, SP odds, pre-race bookmaker odds, and calculated returns.
Clean table with no foreign keys, triggers, or check constraints.
Only racing_bet_data_id, created_at, updated_at are NOT NULL.
Coverage: 95% of fields populated with real data from 2023-01-23 onwards.';

-- STEP 5: Set permissions for Supabase roles
GRANT SELECT, INSERT, UPDATE, DELETE ON rb_odds_historical TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON rb_odds_historical TO service_role;
GRANT USAGE, SELECT ON SEQUENCE rb_odds_historical_racing_bet_data_id_seq TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE rb_odds_historical_racing_bet_data_id_seq TO service_role;

-- STEP 6: Verify table creation
SELECT
    'Table created successfully' as status,
    COUNT(*) as row_count
FROM rb_odds_historical;

-- STEP 7: Show table structure
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'rb_odds_historical'
ORDER BY ordinal_position;

-- =============================================================================
-- DEPLOYMENT NOTES:
-- =============================================================================
-- 1. Before running this script, rename old table:
--    ALTER TABLE rb_odds_historical RENAME TO rb_odds_historical_backup;
--
-- 2. Run this script in Supabase SQL Editor
--
-- 3. Verify creation with: SELECT COUNT(*) FROM rb_odds_historical;
--
-- 4. Test insertion with test_insertion.py
--
-- 5. If successful, optionally migrate data with migrate_from_backup.sql
--
-- 6. Keep rb_odds_historical_backup as safety until confirmed working
-- =============================================================================
