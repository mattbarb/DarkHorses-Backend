# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DarkHorses-Backend-Workers** is the **workers-only** data collection service for horse racing. It fetches both odds data and reference/master data from The Racing API and stores everything in Supabase. The API/frontend is managed in a separate repository and reads from the same database.

## System Architecture

### Workers-Only Architecture

**IMPORTANT**: This repository contains ONLY the background workers - NO API.

The system consists of **TWO separate Render.com deployments**:

1. **Odds Workers Service** (`darkhorses-workers`) - Real-time and historical odds
2. **Masters Worker Service** (`darkhorses-masters-worker`) - Reference data (courses, jockeys, etc.)

All components are organized in dedicated directories:

```
DarkHorses-Backend-Workers/
├── start_workers.py      # Odds workers entry point
├── scheduler.py          # Consolidated scheduler for odds workers
├── requirements.txt      # Odds workers dependencies
├── live-odds-worker/     # Real-time odds collection
│   ├── cron_live.py
│   ├── live_odds_fetcher.py
│   └── live_odds_client.py
├── historical-odds-worker/  # Historical backfill
│   ├── cron_historical.py
│   ├── historical_odds_fetcher.py
│   └── historical_odds_client.py
├── statistics-worker/    # Statistics tracking
│   ├── update_stats.py
│   └── database.py
└── masters-worker/       # Reference data (SEPARATE SERVICE)
    ├── render_worker.py  # Masters worker entry point
    ├── main.py           # CLI orchestrator
    ├── fetchers/         # Entity fetchers
    │   ├── courses_fetcher.py
    │   ├── bookmakers_fetcher.py
    │   ├── jockeys_fetcher.py
    │   ├── trainers_fetcher.py
    │   ├── owners_fetcher.py
    │   ├── horses_fetcher.py
    │   ├── races_fetcher.py
    │   └── results_fetcher.py
    └── requirements.txt  # Masters worker dependencies
```

**Architecture Principle**: TWO separate Render.com services for logical separation:

**Service 1: darkhorses-workers** ($7/month)
- Live odds collection (adaptive: 10s-15min based on race proximity)
- Historical backfill (daily 1 AM)
- Statistics updates (every 10 min)

**Service 2: darkhorses-masters-worker** ($7/month)
- Reference data: courses, bookmakers, jockeys, trainers, owners, horses
- Race cards and results
- Scheduled updates: daily/weekly/monthly

**Total Cost**: $14/month (2 × Render.com Starter plan)

### Database Architecture

**Supabase PostgreSQL Tables** (two categories):

#### Odds Tables (Odds Workers Service)

1. **`ra_odds_live`** (31 columns) - Current/upcoming race odds
   - Fixed odds only (no exchange data)
   - Updated adaptively (10s-15min based on race proximity)
   - Stops updating when race starts
   - Unique constraint: `(race_id, horse_id, bookmaker_id)`

2. **`ra_odds_historical`** - Historical race results and final odds
   - Backfilled from 2015 to present (2.4M+ records)
   - Daily updates at 1:00 AM UK time
   - Includes finishing positions and race results

#### Reference/Master Tables (Masters Worker Service)

3. **`racing_courses`** - Racing venues (UK & Ireland only)
4. **`racing_bookmakers`** - Bookmakers list
5. **`racing_jockeys`** - Jockey profiles
6. **`racing_trainers`** - Trainer profiles
7. **`racing_owners`** - Owner profiles
8. **`racing_horses`** - Horse profiles
9. **`racing_races`** - Race cards with runners
10. **`racing_results`** - Historical race results

**Critical Notes**:
- The Racing API only provides **fixed odds** from traditional bookmakers. Exchange columns were removed.
- All reference data is **filtered for UK/Ireland only** automatically.

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

**Architecture Update** (October 2025):

- **ALL workers** now use Supabase client SDK exclusively
- Statistics tracker refactored from direct PostgreSQL to Supabase SDK

**Why the change**:
- Direct PostgreSQL connection (`db.*.supabase.co`) is IPv6-only and doesn't work from many networks
- Prevented local testing of statistics worker
- Supabase SDK works from anywhere and simplifies configuration

**Implementation**:
- Complex aggregation queries (COUNT DISTINCT, GROUP BY, etc.) are now handled by:
  1. Fetching filtered data via Supabase SDK
  2. Aggregating in Python using native data structures
  3. Fallback to direct PostgreSQL if DATABASE_URL is set (legacy support)

**Configuration**:
```python
# All workers - Supabase SDK only
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_key

# DATABASE_URL no longer required (legacy support only)
```

**Benefits**:
- ✅ Works from any network (local development + Render.com)
- ✅ Eliminates IPv6 connection issues
- ✅ Simpler configuration (2 env vars instead of 3)
- ✅ All tests can run locally without DATABASE_URL

**Files**:
- `statistics-worker/supabase_database.py` - New Supabase SDK adapter
- `statistics-worker/database.py` - Legacy PostgreSQL connection (still available)
- `statistics-worker/update_stats.py` - Auto-detects and uses Supabase SDK first

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

## Masters Worker (Reference Data)

The `masters-worker` is a **separate background service** that fetches and maintains racing reference/master data.

### What It Fetches

**Reference Entities** (UK & Ireland only):
- **Courses** (racing venues) - Monthly updates
- **Bookmakers** (odds providers) - Monthly updates
- **Jockeys** (rider profiles) - Weekly updates
- **Trainers** (trainer profiles) - Weekly updates
- **Owners** (horse owners) - Weekly updates
- **Horses** (horse profiles) - Weekly updates
- **Race Cards** (upcoming races with runners) - Daily updates
- **Race Results** (historical results) - Daily updates

**Regional Filtering**: All data automatically filtered for UK (GB) and Ireland (IRE) only.

### Update Schedule

Runs on scheduled intervals using Python `schedule` library:

```python
# Daily (1:00 AM)
- Race cards (upcoming races)
- Race results (historical)

# Weekly (Sunday 2:00 AM)
- Jockeys
- Trainers
- Owners
- Horses

# Monthly (1st day, 3:00 AM)
- Courses
- Bookmakers
```

### Database Tables

Stores data in separate `racing_*` tables (NOT `ra_odds_*`):
- `racing_courses`
- `racing_bookmakers`
- `racing_jockeys`
- `racing_trainers`
- `racing_owners`
- `racing_horses`
- `racing_races`
- `racing_results`

### Key Files

```
masters-worker/
├── render_worker.py          # Render.com entry point (scheduled execution)
├── main.py                   # CLI orchestrator for manual runs
├── requirements.txt          # Masters worker dependencies
├── config/config.py          # Configuration management
├── fetchers/                 # Entity-specific fetchers
│   ├── courses_fetcher.py
│   ├── bookmakers_fetcher.py
│   ├── jockeys_fetcher.py
│   ├── trainers_fetcher.py
│   ├── owners_fetcher.py
│   ├── horses_fetcher.py
│   ├── races_fetcher.py
│   └── results_fetcher.py
├── utils/
│   ├── api_client.py         # Racing API client
│   ├── supabase_client.py    # Database operations
│   ├── logger.py             # Logging utilities
│   └── regional_filter.py    # UK/Ireland filtering
├── health_check.py           # System health monitoring
├── data_quality_check.py     # Data validation
└── README_WORKER.md          # Masters worker documentation
```

### Manual Execution (Development)

```bash
cd masters-worker

# Fetch all entities (complete sync)
python main.py --all

# Daily update (races and results)
python main.py --daily

# Weekly update (people and horses)
python main.py --weekly

# Monthly update (courses and bookmakers)
python main.py --monthly

# Specific entities
python main.py --entities courses bookmakers
python main.py --entities races results

# Test mode (limited data)
python main.py --test --entities courses
```

## Deployment

### Render.com - TWO Separate Services

**Architecture**: TWO Render.com web services for logical separation.

#### Service 1: Odds Workers (`darkhorses-workers`)

```bash
# Service Configuration (from render.yaml):
Service Name: darkhorses-workers
Service Type: Web Service (needed for always-on)
Build Command: pip install --upgrade pip && pip install -r requirements.txt
Start Command: python3 start_workers.py

# This service runs:
# 1. Live odds scheduler (adaptive intervals)
# 2. Historical odds scheduler (daily 1 AM)
# 3. Statistics updater (every 10 min)
```

**Cost**: $7/month (Render Starter plan)

#### Service 2: Masters Worker (`darkhorses-masters-worker`)

```bash
# Service Configuration (from render.yaml):
Service Name: darkhorses-masters-worker
Service Type: Web Service (needed for always-on)
Root Directory: masters-worker
Build Command: pip install --upgrade pip && pip install -r requirements.txt
Start Command: python3 render_worker.py

# This service runs:
# 1. Reference data fetchers (daily/weekly/monthly schedule)
# 2. Race cards and results (daily)
# 3. People and horses (weekly)
# 4. Courses and bookmakers (monthly)
```

**Cost**: $7/month (Render Starter plan)

### Total System Cost

**$14/month** (2 × Render.com Starter plan)
- Service 1: Odds Workers - $7/month
- Service 2: Masters Worker - $7/month

### Required Environment Variables (Both Services)

**Same variables for both services:**
```
RACING_API_USERNAME=<username>
RACING_API_PASSWORD=<password>
SUPABASE_URL=https://project.supabase.co
SUPABASE_SERVICE_KEY=<service_key>
DATABASE_URL=postgresql://postgres:pass@db.supabase.co:5432/postgres
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

### Critical Deployment Requirements

- **Plan**: Must use Starter ($7/month) or higher - NOT free tier
- **Why**: Free tier spins down after 15 min, stopping schedulers
- **Config File**: `render.yaml` in repository root defines BOTH services
- **Deployment**: Pushing to GitHub auto-deploys both services

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
