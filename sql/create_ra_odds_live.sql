-- Create live odds tables with ra_ prefix naming convention
-- Run this in Supabase SQL Editor

-- Drop and recreate tables to ensure correct structure
DROP TABLE IF EXISTS ra_odds_live CASCADE;
DROP TABLE IF EXISTS ra_bookmakers CASCADE;
DROP TABLE IF EXISTS ra_odds_statistics CASCADE;

-- Main live odds table - captures ALL bookmaker odds
CREATE TABLE ra_odds_live (
    id BIGSERIAL PRIMARY KEY,

    -- Unique identifiers
    race_id TEXT NOT NULL,
    horse_id TEXT NOT NULL,
    bookmaker_id TEXT NOT NULL,

    -- Race metadata
    race_date DATE NOT NULL,
    race_time TIME,
    off_dt TIMESTAMPTZ,
    course TEXT NOT NULL,
    race_name TEXT,
    race_class TEXT,
    race_type TEXT,
    distance TEXT,
    going TEXT,
    runners INTEGER,

    -- Horse metadata
    horse_name TEXT NOT NULL,
    horse_number INTEGER,
    jockey TEXT,
    trainer TEXT,
    draw INTEGER,
    weight TEXT,
    age INTEGER,
    form TEXT,

    -- Bookmaker information
    bookmaker_name TEXT NOT NULL,
    bookmaker_type TEXT, -- 'exchange' or 'fixed'
    market_type TEXT DEFAULT 'WIN',

    -- Odds data (current snapshot)
    odds_decimal NUMERIC(10,3),
    odds_fractional TEXT,
    back_price NUMERIC(10,3), -- For exchanges like Betfair
    lay_price NUMERIC(10,3),  -- For exchanges
    back_size NUMERIC(12,2),  -- Available to back
    lay_size NUMERIC(12,2),   -- Available to lay

    -- Market depth for exchanges
    back_prices JSONB, -- Top 3 back prices [{price, size}]
    lay_prices JSONB,  -- Top 3 lay prices
    total_matched NUMERIC(15,2),

    -- Status
    market_status TEXT DEFAULT 'OPEN',
    in_play BOOLEAN DEFAULT FALSE,

    -- Timestamps
    odds_timestamp TIMESTAMPTZ NOT NULL, -- When odds were captured from API
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique current odds per bookmaker
    UNIQUE(race_id, horse_id, bookmaker_id)
);

-- Create indexes for fast queries
CREATE INDEX idx_ra_odds_live_race_date ON ra_odds_live(race_date);
CREATE INDEX idx_ra_odds_live_race_id ON ra_odds_live(race_id);
CREATE INDEX idx_ra_odds_live_horse_id ON ra_odds_live(horse_id);
CREATE INDEX idx_ra_odds_live_bookmaker ON ra_odds_live(bookmaker_id);
CREATE INDEX idx_ra_odds_live_course ON ra_odds_live(course);
CREATE INDEX idx_ra_odds_live_timestamp ON ra_odds_live(odds_timestamp);
CREATE INDEX idx_ra_odds_live_off_dt ON ra_odds_live(off_dt);

-- Composite index for common queries
CREATE INDEX idx_ra_odds_live_race_horse_book ON ra_odds_live(race_id, horse_id, bookmaker_id);

-- Bookmaker reference table
CREATE TABLE ra_bookmakers (
    bookmaker_id TEXT PRIMARY KEY,
    bookmaker_name TEXT NOT NULL,
    bookmaker_type TEXT NOT NULL, -- 'exchange' or 'fixed'
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert known bookmakers
INSERT INTO ra_bookmakers (bookmaker_id, bookmaker_name, bookmaker_type) VALUES
    -- Exchanges
    ('betfair', 'Betfair', 'exchange'),
    ('smarkets', 'Smarkets', 'exchange'),
    ('matchbook', 'Matchbook', 'exchange'),
    ('betdaq', 'Betdaq', 'exchange'),
    -- Major fixed odds bookmakers
    ('bet365', 'Bet365', 'fixed'),
    ('williamhill', 'William Hill', 'fixed'),
    ('paddypower', 'Paddy Power', 'fixed'),
    ('ladbrokes', 'Ladbrokes', 'fixed'),
    ('coral', 'Coral', 'fixed'),
    ('skybet', 'Sky Bet', 'fixed'),
    ('betfred', 'Betfred', 'fixed'),
    ('unibet', 'Unibet', 'fixed'),
    ('betvictor', 'BetVictor', 'fixed'),
    ('betway', 'Betway', 'fixed'),
    ('boylesports', 'BoyleSports', 'fixed'),
    ('888sport', '888 Sport', 'fixed');

-- Statistics table for monitoring fetches
CREATE TABLE ra_odds_statistics (
    id SERIAL PRIMARY KEY,
    fetch_timestamp TIMESTAMPTZ NOT NULL,
    race_id TEXT,
    races_count INTEGER DEFAULT 0,
    horses_count INTEGER DEFAULT 0,
    bookmakers_found INTEGER DEFAULT 0,
    total_odds_fetched INTEGER DEFAULT 0,
    bookmaker_list TEXT[], -- Array of bookmaker IDs found
    fetch_duration_ms NUMERIC,
    errors_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ra_odds_stats_timestamp ON ra_odds_statistics(fetch_timestamp);
CREATE INDEX idx_ra_odds_stats_race ON ra_odds_statistics(race_id);

-- Verify tables were created
SELECT 'Tables created:' as info;
SELECT table_name, pg_size_pretty(pg_total_relation_size(table_name::regclass)) as size
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('ra_odds_live', 'ra_bookmakers', 'ra_odds_statistics')
ORDER BY table_name;