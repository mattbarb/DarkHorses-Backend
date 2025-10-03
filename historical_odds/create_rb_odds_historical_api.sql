-- ============================================================================
-- RB_ODDS_HISTORICAL_API TABLE
-- Historical odds data from Racing API (completed races at race start time)
-- ============================================================================

-- Drop table if exists (for clean re-creation)
DROP TABLE IF EXISTS rb_odds_historical_api CASCADE;

-- Create the historical odds table for Racing API data
CREATE TABLE rb_odds_historical_api (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Race identifiers
    race_id TEXT NOT NULL,
    horse_id TEXT NOT NULL,
    bookmaker_id TEXT NOT NULL,

    -- Race metadata
    race_date DATE NOT NULL,
    course TEXT NOT NULL,
    off_time TIME,
    off_dt TIMESTAMPTZ,
    race_name TEXT,
    race_class TEXT,
    race_type TEXT,
    distance TEXT,
    distance_f NUMERIC,
    going TEXT,
    prize_money TEXT,
    num_runners INTEGER,

    -- Horse metadata
    horse_name TEXT NOT NULL,
    jockey TEXT,
    jockey_id TEXT,
    trainer TEXT,
    trainer_id TEXT,
    draw INTEGER,
    weight TEXT,
    age INTEGER,
    horse_form TEXT,

    -- Race result data
    starting_price TEXT,
    sp_decimal NUMERIC,
    finishing_position INTEGER,
    distance_behind TEXT,
    official_result TEXT,

    -- Bookmaker odds data (at race start)
    bookmaker_name TEXT NOT NULL,
    odds_decimal NUMERIC NOT NULL,
    odds_fractional TEXT,

    -- Timestamps
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint to prevent duplicates
    UNIQUE(race_id, horse_id, bookmaker_id)
);

-- Create indexes for common queries
CREATE INDEX idx_rb_odds_hist_api_race_date ON rb_odds_historical_api(race_date);
CREATE INDEX idx_rb_odds_hist_api_race_id ON rb_odds_historical_api(race_id);
CREATE INDEX idx_rb_odds_hist_api_horse_id ON rb_odds_historical_api(horse_id);
CREATE INDEX idx_rb_odds_hist_api_bookmaker_id ON rb_odds_historical_api(bookmaker_id);
CREATE INDEX idx_rb_odds_hist_api_course ON rb_odds_historical_api(course);
CREATE INDEX idx_rb_odds_hist_api_finishing_position ON rb_odds_historical_api(finishing_position);

-- Create composite index for common race + date queries
CREATE INDEX idx_rb_odds_hist_api_race_date_course ON rb_odds_historical_api(race_date, course);

-- Create index for analysis queries
CREATE INDEX idx_rb_odds_hist_api_bookmaker_date ON rb_odds_historical_api(bookmaker_id, race_date);

-- Add comments for documentation
COMMENT ON TABLE rb_odds_historical_api IS 'Historical odds data from Racing API. Captures final odds at race start time for all horses and bookmakers.';
COMMENT ON COLUMN rb_odds_historical_api.race_id IS 'Unique race identifier from Racing API';
COMMENT ON COLUMN rb_odds_historical_api.horse_id IS 'Unique horse identifier from Racing API';
COMMENT ON COLUMN rb_odds_historical_api.bookmaker_id IS 'Unique bookmaker identifier';
COMMENT ON COLUMN rb_odds_historical_api.odds_decimal IS 'Decimal odds (e.g., 3.50 for 5/2)';
COMMENT ON COLUMN rb_odds_historical_api.odds_fractional IS 'Fractional odds (e.g., "5/2")';
COMMENT ON COLUMN rb_odds_historical_api.starting_price IS 'Official starting price from Racing API';
COMMENT ON COLUMN rb_odds_historical_api.finishing_position IS 'Final position in race (1 = winner)';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON rb_odds_historical_api TO authenticated;
GRANT SELECT, INSERT, UPDATE ON rb_odds_historical_api TO service_role;