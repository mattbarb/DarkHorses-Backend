# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DarkHorses Odds API is a comprehensive horse racing odds collection system that fetches data from The Racing API and stores it in Supabase. The system runs as a unified Odds API with all components consolidated into a single process.

## System Architecture

### Unified Odds API Architecture

**IMPORTANT**: This system runs as ONE Render.com web service - the **Odds API**.

All components are organized under the `odds_api/` directory:

```
odds_api/
├── start.py              # Main entry - runs API + scheduler together
├── main.py               # FastAPI app + dashboard UI
├── scheduler.py          # Background worker for all data collection
├── static/               # Dashboard UI assets
├── logs/                 # All service logs
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

**Key principle**: ONE process, ONE service, ONE deployment:
- FastAPI server (API + Dashboard UI)
- Live odds collection (every 5 min)
- Historical backfill (daily 1 AM)
- Statistics updates (every 10 min)

**Cost savings**: $7/month for ONE unified service instead of $21/month for three separate workers.

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

### Unified Odds API (Recommended)

```bash
# Single command runs the complete Odds API
cd odds_api
python3 start.py

# Access dashboard at http://localhost:8000
# API docs at http://localhost:8000/docs
```

This starts the complete Odds API:
- FastAPI server (API + UI)
- Live odds scheduler (every 5 min)
- Historical odds scheduler (daily 1 AM)
- Statistics updater (every 10 min)

### Individual Modules (Development/Testing)

```bash
# Live odds only
cd odds_api/live_odds
python3 cron_live.py

# Historical odds only
cd odds_api/historical_odds
python3 cron_historical.py

# Statistics only
cd odds_api/odds_statistics
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

**Live Odds** (`api/scheduler.py` line ~48):
```python
schedule.every(5).minutes.do(self.run_live_odds)
```

**Historical Odds** (`api/scheduler.py` line ~51):
```python
schedule.every().day.at("01:00").do(self.run_historical_odds)
```

**Statistics** (`api/scheduler.py` line ~54):
```python
schedule.every(10).minutes.do(self.run_statistics_update)
```

Also triggered automatically after successful fetch cycles in both live and historical schedulers.

## API Endpoints

### Core Endpoints
- `GET /` - Dashboard UI
- `GET /health` - Health check
- `GET /docs` - Swagger documentation
- `GET /api/scheduler-status` - Shows scheduler configuration and timing

### Data Endpoints
- `GET /api/live-odds` - Query live odds with filters (race_date, course, bookmaker)
- `GET /api/live-odds/upcoming-races` - Races in next 24 hours
- `GET /api/historical-odds` - Historical odds with filters (year, course, race_date)
- `GET /api/statistics` - Latest statistics from JSON files
- `GET /api/bookmakers` - List of all bookmakers
- `GET /api/courses` - List of all courses/tracks

## Deployment

### Render.com - Unified Odds API Deployment (Production)

**Architecture**: ONE Render.com web service runs the complete Odds API.

```bash
# Service Configuration:
Service Name: darkhorses-odds-api
Service Type: Web Service
Root Directory: odds_api
Build Command: pip install -r ../requirements.txt
Start Command: python3 start.py

# This ONE service provides:
# 1. Complete Odds API (FastAPI server + Dashboard UI)
# 2. Live odds scheduler (every 5 min)
# 3. Historical odds scheduler (daily 1 AM)
# 4. Statistics updater (every 10 min)
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
- **Cost**: $7/month for ONE service = API + all schedulers
- **Config File**: Use `/api/render.yaml` (not root `/render.yaml`)

The consolidated deployment saves money by running everything in ONE process instead of separate microservices.

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
3. Root directory not set to `odds_api` in render.yaml
4. Using `uvicorn main:app` instead of `python3 start.py`

## Testing

### Manual Testing

```bash
# Test live odds fetch
curl "http://localhost:8000/api/live-odds?limit=10"

# Test upcoming races
curl "http://localhost:8000/api/live-odds/upcoming-races"

# Test statistics
curl "http://localhost:8000/api/statistics?table=all"

# Test scheduler status
curl "http://localhost:8000/api/scheduler-status"
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

### Core Odds API Files
- `odds_api/start.py` - Main entry point for Odds API
- `odds_api/main.py` - FastAPI application with all endpoints
- `odds_api/scheduler.py` - Background worker running all schedulers
- `odds_api/static/index.html` - Dashboard UI

### Live Odds Module
- `odds_api/live_odds/cron_live.py` - Live odds scheduler (lines 122, 271 are critical)
- `odds_api/live_odds/live_odds_fetcher.py` - Parses embedded odds from Racing API
- `odds_api/live_odds/live_odds_client.py` - Supabase upsert operations

### Historical Odds Module
- `odds_api/historical_odds/cron_historical.py` - Historical odds scheduler
- `odds_api/historical_odds/historical_odds_fetcher.py` - Fetches historical data
- `odds_api/historical_odds/historical_odds_client.py` - Supabase client

### Statistics Module
- `odds_api/odds_statistics/update_stats.py` - Statistics updater
- `odds_api/odds_statistics/database.py` - Direct PostgreSQL for statistics queries

### Schema and Configuration
- `sql/create_ra_odds_live.sql` - Live odds table schema (31 columns)
- `sql/create_ra_odds_historical.sql` - Historical odds table schema
- `sql/migrate_remove_exchange_columns.sql` - Exchange columns removal migration
- `render.yaml` - Render.com deployment configuration

## Development Workflow

1. **Make changes** to any component (API, scheduler, fetcher, etc.)
2. **Test locally** with `cd odds_api && python3 start.py`
3. **Verify** data flow: Racing API → Parser → Database → Statistics → API
4. **Check logs** in `odds_api/logs/scheduler.log` for errors
5. **Deploy** by pushing to GitHub (Render auto-deploys)

## Performance Notes

- Expected load: ~50 database queries/min (scheduler + API)
- Memory usage: ~200-400MB for consolidated system
- API handles ~1000 req/min on Starter plan
- Live odds updates: ~858 odds per 3 races (26 bookmakers × 33 horses)
- Historical backfill rate: ~100 dates per cycle

## Schema Evolution

The `ra_odds_live` table was reduced from 38 to 31 columns by removing unused exchange odds fields. See `sql/README_SCHEMA_CHANGES.md` for full migration details. This is the only major schema change - the system is otherwise stable.
