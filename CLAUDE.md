# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DarkHorses-Backend-Workers** is the **workers-only** data collection service for horse racing odds. It fetches data from The Racing API and stores it in Supabase. The API/frontend is managed in a separate repository and reads from the same database.

## System Architecture

### Workers-Only Architecture

**IMPORTANT**: This repository contains ONLY the background workers - NO API.

All components are organized under the `workers/` directory:

```
workers/
├── start_workers.py      # Main entry - runs all schedulers
├── scheduler.py          # Consolidated scheduler for all workers
├── requirements.txt      # Worker dependencies
├── logs/                 # All worker logs
├── live_odds/            # Real-time odds collection module
│   ├── cron_live.py
│   ├── live_odds_fetcher.py
│   └── live_odds_client.py
├── historical_odds/      # Historical backfill module
│   ├── cron_historical.py
│   ├── historical_odds_fetcher.py
│   └── historical_odds_client.py
└── odds_statistics/      # Statistics tracking module
    ├── update_stats.py
    └── database.py
```

**Key principle**: ONE Render.com web service runs all data collection:
- Live odds collection (adaptive: 10s-15min based on race proximity)
- Historical backfill (daily 1 AM)
- Statistics updates (every 10 min)
- NO HTTP server, NO API endpoints

**Cost**: $7/month for ONE workers service on Render.com Starter plan.

### Database Architecture

**Two main tables in Supabase PostgreSQL:**

1. **`ra_odds_live`** (31 columns) - Current/upcoming race odds
   - Fixed odds only (no exchange data)
   - Updated every 5 minutes (adaptive: 1 min when race imminent)
   - Stops updating when race starts
   - Unique constraint: `(race_id, horse_id, bookmaker_id)`

2. **`ra_odds_historical`** - Historical race results and final odds
   - Backfilled from 2015 to present
   - Daily updates at 1:00 AM UK time
   - Includes finishing positions and race results

**Critical Note**: The Racing API only provides **fixed odds** from traditional bookmakers. Exchange columns (back/lay prices, etc.) were removed as they're never populated.

### Data Flow

```
Racing API (/racecards/pro)
    ↓
Embedded Odds Parser (parse_embedded_odds)
    ↓
Supabase Upsert (handles duplicates via unique constraint)
    ↓
Statistics Auto-Update (after successful fetch)
    ↓
JSON Output (odds_statistics/output/*.json)
```

## Running the System

### Consolidated Workers (Recommended)

```bash
# Single command runs all workers
cd workers
python3 start_workers.py
```

This starts all data collection workers:
- Live odds scheduler (adaptive intervals)
- Historical odds scheduler (daily 1 AM)
- Statistics updater (every 10 min)
- NO HTTP server

### Individual Modules (Development/Testing)

```bash
# Live odds only
cd workers/live_odds
python3 cron_live.py

# Historical odds only
cd workers/historical_odds
python3 cron_historical.py

# Statistics only
cd workers/odds_statistics
python3 update_stats.py --table all
```

## Key Implementation Details

### Live Odds Critical Bug Fix (Line Numbers Important)

**File**: `live_odds/cron_live.py`

**Line 122** - Race filtering logic:
```python
# CORRECT (current):
if time_until_race >= 0:  # No upper limit - fetch all races today

# WRONG (previous bug):
if -10 <= time_until_race <= 180:  # Skipped races >3 hours away
```

**Line 271** - Odds fetching:
```python
# CORRECT (current):
odds_data = self.fetcher.parse_embedded_odds(runner, race_id)

# WRONG (deprecated):
odds_data = self.fetcher.fetch_live_odds(race_id, horse_id)
```

The Racing API changed - odds are now embedded in racecards, not in a separate endpoint.

### Embedded Odds Parsing

**Critical field name**: `runner['odds']` NOT `runner['pre_race_odds']`

The parser extracts 26 bookmakers per horse from the embedded `odds` array in each runner object.

### Statistics Tracker Database Connection

**Important architectural decision**:

- **Main pipeline** (live_odds, historical_odds): Uses Supabase client SDK
- **Statistics tracker**: Uses direct PostgreSQL connection via `psycopg2`

**Reason**: Supabase client doesn't support complex aggregation queries (COUNT DISTINCT, GROUP BY with aggregations, etc.) needed for statistics. Direct PostgreSQL is read-only for analytics.

**Configuration**:
```python
# Main pipeline - Supabase SDK
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_key

# Statistics tracker - Direct PostgreSQL (read-only)
DATABASE_URL=postgresql://postgres:password@db.supabase.co:5432/postgres
```

### Scheduler Timing

**Live Odds** (`workers/scheduler.py` - adaptive scheduling):
```python
# Dynamic intervals based on race proximity:
# - 10s when race imminent (<5 min)
# - 60s when race soon (<30 min)
# - 5 min when race upcoming (<2 hours)
# - 15 min default check interval
```

**Historical Odds** (`workers/scheduler.py` line ~160):
```python
schedule.every().day.at("01:00").do(self.run_historical_odds)
```

**Statistics** (`workers/scheduler.py` line ~164):
```python
schedule.every(10).minutes.do(self.run_statistics_update)
```

Also triggered automatically after successful fetch cycles in both live and historical schedulers.

## Deployment

### Render.com - Workers Deployment (Production)

**Architecture**: ONE Render.com web service runs all background workers.

```bash
# Service Configuration (from render.yaml):
Service Name: darkhorses-workers
Service Type: Web Service (needed for always-on)
Root Directory: workers
Build Command: pip install -r requirements.txt
Start Command: python3 start_workers.py

# This ONE service runs:
# 1. Live odds scheduler (adaptive intervals)
# 2. Historical odds scheduler (daily 1 AM)
# 3. Statistics updater (every 10 min)
# NO HTTP server, NO API
```

**Required Environment Variables:**
```
RACING_API_USERNAME=<username>
RACING_API_PASSWORD=<password>
SUPABASE_URL=https://project.supabase.co
SUPABASE_SERVICE_KEY=<service_key>
DATABASE_URL=postgresql://postgres:pass@db.supabase.co:5432/postgres
```

**Critical Deployment Requirements:**
- **Plan**: Must use Starter ($7/month) or higher - NOT free tier
- **Why**: Free tier spins down after 15 min, stopping schedulers
- **Cost**: $7/month for ONE workers service
- **Config File**: `render.yaml` in root

**Note**: The API/frontend is deployed separately in a different repository.

### Environment Variables

**Required for all deployments**:
```
RACING_API_USERNAME=<username>
RACING_API_PASSWORD=<password>
SUPABASE_URL=https://project.supabase.co
SUPABASE_SERVICE_KEY=<service_key>
DATABASE_URL=postgresql://postgres:pass@db.supabase.co:5432/postgres
```

**Optional**:
```
PORT=8000
LOG_LEVEL=INFO
MONITOR_ENABLED=false  # Set to true for monitoring server
```

## Common Issues and Solutions

### Issue: Live odds not collecting data
**Symptom**: Scheduler finds races but inserts 0 odds

**Root cause**: Using deprecated `fetch_live_odds()` method or wrong field name

**Solution**: Ensure `cron_live.py:271` calls `parse_embedded_odds()` and looks for `runner['odds']` field

### Issue: Races being skipped as ">3 hours away"
**Symptom**: Log shows "Skipped X races (all >3 hours away)"

**Root cause**: Hardcoded time filter on line 122

**Solution**: Change to `if time_until_race >= 0:` (no upper limit)

### Issue: Statistics not updating
**Symptom**: JSON files in `odds_statistics/output/` are stale

**Solutions**:
1. Check `DATABASE_URL` is set (not just SUPABASE_URL)
2. Verify direct PostgreSQL connection works
3. Check statistics module imports successfully in schedulers
4. Run manually: `cd odds_statistics && python3 update_stats.py --table all`

### Issue: Exchange columns always NULL
**Solution**: This is expected - Racing API doesn't provide exchange odds. Columns were removed in schema migration (see `sql/README_SCHEMA_CHANGES.md`).

### Issue: Render deployment fails
**Common causes**:
1. Free tier selected (needs Starter for always-on scheduler)
2. Missing environment variables
3. Root directory not set to `workers` in render.yaml
4. Wrong start command (should be `python3 start_workers.py`)

## Testing

### Local Testing

```bash
# Run workers locally
cd workers
python3 start_workers.py

# Check logs
tail -f workers/logs/scheduler.log
tail -f workers/logs/workers.log
```

### Database Verification

```sql
-- Check live odds collection
SELECT
    COUNT(*) as total_records,
    COUNT(DISTINCT race_id) as unique_races,
    MAX(fetched_at) as last_fetch
FROM ra_odds_live
WHERE race_date >= CURRENT_DATE;

-- Check historical coverage
SELECT
    MIN(race_date) as earliest,
    MAX(race_date) as latest,
    COUNT(DISTINCT race_date) as dates_covered
FROM ra_odds_historical;

-- Verify no exchange columns exist
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'ra_odds_live'
AND column_name LIKE '%back%' OR column_name LIKE '%lay%';
-- Should return 0 rows
```

## Important Files Reference

### Core Workers Files
- `workers/start_workers.py` - Main entry point for all workers
- `workers/scheduler.py` - Consolidated scheduler running all data collection
- `workers/requirements.txt` - Worker dependencies

### Live Odds Module
- `workers/live_odds/cron_live.py` - Live odds scheduler (lines 122, 271 are critical)
- `workers/live_odds/live_odds_fetcher.py` - Parses embedded odds from Racing API
- `workers/live_odds/live_odds_client.py` - Supabase upsert operations

### Historical Odds Module
- `workers/historical_odds/cron_historical.py` - Historical odds scheduler
- `workers/historical_odds/historical_odds_fetcher.py` - Fetches historical data
- `workers/historical_odds/historical_odds_client.py` - Supabase client

### Statistics Module
- `workers/odds_statistics/update_stats.py` - Statistics updater
- `workers/odds_statistics/database.py` - Direct PostgreSQL for statistics queries

### Schema and Configuration
- `sql/create_ra_odds_live.sql` - Live odds table schema (31 columns)
- `sql/create_ra_odds_historical.sql` - Historical odds table schema
- `sql/migrate_remove_exchange_columns.sql` - Exchange columns removal migration
- `render.yaml` - Render.com deployment configuration

## Development Workflow

1. **Make changes** to any component (scheduler, fetcher, etc.)
2. **Test locally** with `cd workers && python3 start_workers.py`
3. **Verify** data flow: Racing API → Parser → Database → Statistics
4. **Check logs** in `workers/logs/scheduler.log` for errors
5. **Deploy** by pushing to GitHub (Render auto-deploys)

## Performance Notes

- Expected load: ~50 database writes/min (schedulers only)
- Memory usage: ~200-300MB for workers
- Live odds updates: ~858 odds per 3 races (26 bookmakers × 33 horses)
- Historical backfill rate: ~100 dates per cycle
- No HTTP traffic (workers-only service)

## Schema Evolution

The `ra_odds_live` table was reduced from 38 to 31 columns by removing unused exchange odds fields. See `sql/README_SCHEMA_CHANGES.md` for full migration details. This is the only major schema change - the system is otherwise stable.
