-- Migration: Remove unused exchange odds columns from ra_odds_live
-- These columns are never populated because the Racing API doesn't provide exchange data
-- Run this in Supabase SQL Editor

BEGIN;

-- Remove exchange-specific columns that are always NULL
ALTER TABLE ra_odds_live
DROP COLUMN IF EXISTS back_price,
DROP COLUMN IF EXISTS lay_price,
DROP COLUMN IF EXISTS back_size,
DROP COLUMN IF EXISTS lay_size,
DROP COLUMN IF EXISTS back_prices,
DROP COLUMN IF EXISTS lay_prices,
DROP COLUMN IF EXISTS total_matched;

-- Set default for bookmaker_type since we only have 'fixed' bookmakers
ALTER TABLE ra_odds_live
ALTER COLUMN bookmaker_type SET DEFAULT 'fixed';

-- Add comment to clarify current limitations
COMMENT ON TABLE ra_odds_live IS
'Live odds table - Currently supports FIXED ODDS ONLY. Exchange odds (Betfair, Smarkets) not available via Racing API racecards endpoint.';

COMMENT ON COLUMN ra_odds_live.bookmaker_type IS
'Type of bookmaker: fixed (traditional bookmakers). Exchange type not currently supported.';

COMMENT ON COLUMN ra_odds_live.odds_decimal IS
'Decimal odds from fixed odds bookmakers (e.g., 5.0 for 4/1). Exchange back/lay prices not available.';

COMMIT;

-- Verify changes
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'ra_odds_live'
ORDER BY ordinal_position;
