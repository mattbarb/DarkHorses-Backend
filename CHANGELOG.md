# Changelog

All notable changes to the DarkHorses Odds Workers project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2025-10-13

### Added

#### Race Name Field in Historical Odds
- **Missing field identified** - `ra_odds_historical` table was missing `race_name` field (e.g., "THE RAY HAWTHORNE MEMORIAL AMATEUR")
- **Database migration** - Added `race_name TEXT` column with index to `ra_odds_historical` table
- **Schema mapping updated** - Historical odds fetcher now stores race names from Racing API
- **Backfill script** - Intelligent backfill for existing 2.4M+ records
- **Parity with live odds** - Both live and historical tables now include race name

**Files Modified**:
- `sql/add_race_name_to_historical.sql` (NEW, 65 lines) - Database migration script
- `historical-odds-worker/schema_mapping.py` (Line 382) - Added race_name to schema mapping
- `sql/backfill_race_names.py` (NEW, 327 lines) - Intelligent backfill script
- `docs/RACE_NAME_FIX.md` (NEW) - Complete deployment guide

**Root Cause**:
1. Historical fetcher WAS capturing `race_name` from Racing API (line 254 in `historical_odds_fetcher.py`)
2. Database schema DID NOT have `race_name` column
3. Schema mapper WAS NOT including `race_name` in mapped records (missing from line 382)

**Solution**:
```sql
-- Database migration
ALTER TABLE ra_odds_historical ADD COLUMN race_name TEXT;
CREATE INDEX idx_ra_odds_historical_race_name ON ra_odds_historical (race_name);
```

```python
# Schema mapping update (historical-odds-worker/schema_mapping.py:382)
'race_name': combined_data.get('race_name'),  # NEW LINE
'going': combined_data.get('going'),
```

**Backfill Process**:
- Fetches records with NULL `race_name`
- Groups by unique race (date, track, time)
- Queries Racing API results endpoint for race names
- Updates all matching records efficiently
- Handles ~2.4M records in 4-8 hours with rate limiting

**Usage**:
```bash
# Test backfill
python3 sql/backfill_race_names.py --dry-run --max-races 10

# Run backfill
python3 sql/backfill_race_names.py --batch-size 10000
```

**API Impact**:
- ~40K unique races to backfill
- ~40K API calls (well within 100K/month limit)
- 0.2s delay between calls (rate limiting)
- Total backfill time: 4-8 hours

**Verification**:
```sql
-- Check completion
SELECT
    COUNT(*) as total_records,
    COUNT(race_name) as records_with_race_name,
    (COUNT(race_name)::float / COUNT(*) * 100)::numeric(5,2) as completion_pct
FROM ra_odds_historical;

-- View sample race names
SELECT race_name, COUNT(*)
FROM ra_odds_historical
WHERE race_name IS NOT NULL
GROUP BY race_name
ORDER BY COUNT(*) DESC
LIMIT 10;
```

**Deployment Steps**:
1. ✅ Run database migration (`add_race_name_to_historical.sql`)
2. ✅ Deploy code changes (auto-deploy on git push)
3. ⏳ Run backfill script for existing records
4. ✅ Verify new records include race_name
5. ✅ Update API documentation

**Files Created**:
- `sql/add_race_name_to_historical.sql` - Database migration
- `sql/backfill_race_names.py` - Backfill script with dry-run mode
- `docs/RACE_NAME_FIX.md` - Complete deployment and troubleshooting guide

---

## [1.2.0] - 2025-10-09

### Added

#### Change Detection Optimization
- **Intelligent odds comparison** - Only updates database when `odds_decimal` values actually change
- **Bulk existing odds fetch** - Single query fetches existing odds for all races in batch (~100ms)
- **Skip statistics tracking** - New `skipped` field in return values shows unchanged records
- **Cost savings logging** - Shows database writes avoided in each cycle
- **Comprehensive test suite** - `test_change_detection.py` validates change detection logic

**Files Modified**:
- `live-odds-worker/live_odds_client.py` (+185 lines)
  - New method: `fetch_existing_odds_for_races()` (Lines 69-108)
  - Updated: `update_live_odds()` with change detection (Lines 110-234)
  - Updated: `_process_bookmaker_batch()` with insert/update tracking (Lines 236-273)
- `live-odds-worker/cron_live.py` (+18 lines)
  - Extract race IDs for bulk fetch
  - Pass race_ids to update method
  - Enhanced logging with skip counts

**Performance Impact**:
```
Before: 150,000 database writes per hour
After:  6,000-30,000 writes per hour (80-95% reduction)
```

**Expected Log Output**:
```
✅ Records inserted: 0 (new)
✅ Records updated: 127 (odds changed)
✅ Records skipped: 2,457 (odds unchanged)
💰 Database cost savings: 2,457 unnecessary writes avoided
```

#### Redis Cache Invalidation
- **Automatic cache invalidation** - Workers invalidate API cache after database updates
- **Upstash Redis integration** - REST-based Redis client for cache management
- **Graceful degradation** - Falls back to TTL-only caching if Redis unavailable
- **Non-blocking** - Cache failures won't break worker operations

**Files Modified**:
- `redis_cache.py` (NEW, 90 lines) - Simple Redis client for invalidation
- `live-odds-worker/live_odds_client.py` (Lines 6-28, 268-270) - Added cache invalidation call
- `requirements.txt` - Added `upstash-redis==0.15.0`

**Configuration**:
```bash
UPSTASH_REDIS_REST_URL=https://wise-crab-11560.upstash.io
UPSTASH_REDIS_REST_TOKEN=<token>
```

**System Flow**:
```
Workers update DB → Invalidate cache → Next API request fetches fresh data
```

### Fixed

#### Frontend UI Hang on "Updating now..."
**Severity**: CRITICAL - User-facing issue

**Problem**: Frontend displays "Updating now..." for 15+ seconds and appears to hang indefinitely.

**Root Cause**: Bulk fetch was querying ALL upcoming races (50-100+ races, 82,000+ rows) instead of only races in current update batch (2-5 races, 2,500 rows). Large query took 5-15 seconds, blocking frontend SELECT queries.

**Solution**: Extract race_ids from actual update records, not from all upcoming races.

**Files Modified**:
- `live-odds-worker/cron_live.py` (Lines 403-411)
  - Changed: `race_ids_list = [race.get('race_id') for race in races]`
  - To: `race_ids_in_batch = list(set(record.get('race_id') for record in all_odds_records))`
- `live-odds-worker/live_odds_client.py` (Lines 84-90)
  - Added safeguard warning if >20 races queried
  - Prevents accidentally reintroducing the bug

**Performance Comparison**:
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Race IDs queried | 96 | 3 | **32x fewer** |
| Rows fetched | 82,368 | 2,574 | **32x fewer** |
| Bulk fetch time | 5-15s | <1s | **15x faster** |
| Table lock duration | 5-15s | <1s | **15x shorter** |
| Frontend response | 15+ seconds | <2 seconds | **8x faster** |

**Visual Explanation**:
```
BEFORE FIX:
T+0s:  User loads page → "Updating now..."
T+2s:  Backend starts bulk fetch (96 races, 82k rows)
T+17s: Bulk fetch completes, frontend query executes
Result: User sees "Updating now..." for 15+ seconds (appears frozen)

AFTER FIX:
T+0s:  User loads page → "Updating now..."
T+2s:  Backend starts bulk fetch (3 races, 2.5k rows)
T+3s:  Bulk fetch completes, frontend query executes
Result: User sees "Updating now..." for <2 seconds (fast and responsive)
```

**Commit**: `98265c9` - Fix: Optimize bulk fetch to prevent frontend hangs

### Performance

#### Database Write Optimization
**Reduction**: 80-95% fewer database writes during stable odds periods

**Metrics**:
- **Cycle duration**: 2,500ms → 650-1,150ms (54-74% faster)
- **Writes per hour**: 150,000 → 6,000-30,000 (80-96% reduction)
- **Writes per day**: 3.6M → 144K-720K (80-96% reduction)
- **Monthly savings**: ~54M unnecessary writes avoided

**Cost Impact**:
- Significant reduction in Supabase database costs
- More efficient resource utilization
- Reduced database load

#### Query Performance
**Frontend response time**:
- Before: 15+ seconds (hanging)
- After: <2 seconds (fast and responsive)

**Backend fetch cycles**:
- Bulk fetch: 5-15s → <1s (15x faster)
- Table locks: 5-15s → <1s (15x shorter)
- No more concurrent query blocking

---

## [1.1.0] - 2025-10-06

### Changed

#### Architecture Restructure: Microservices → Consolidated Service
**Objective**: Simplify deployment and reduce costs by consolidating services

**Before (Microservices)**:
```
3 separate worker services:
- live-odds-worker/
- historical-odds-worker/
- statistics-worker/

Cost: $21/month (3 × $7/month)
Deployment: 3 separate Render.com services
```

**After (Consolidated)**:
```
Single unified service:
- workers/
  ├── start_workers.py
  ├── scheduler.py
  ├── live_odds/
  ├── historical_odds/
  └── odds_statistics/

Cost: $7/month (1 service)
Deployment: Single Render.com service
```

**Benefits**:
- **Cost savings**: $21/month → $7/month (67% reduction)
- **Simpler deployment**: 1 service instead of 3
- **Easier monitoring**: Single log stream
- **Unified configuration**: One set of environment variables
- **No inter-service communication**: All workers in one process

**Tradeoffs**:
- Less granular scaling (scale all workers together)
- Single point of failure (if service crashes, all workers stop)
- Shared resource limits

**Files Created**:
- `workers/start_workers.py` - Main entry point for all workers
- `workers/scheduler.py` - Consolidated scheduler running all data collection
- `render.yaml` - Single service deployment configuration

**Deployment**:
- Service Name: `darkhorses-workers`
- Type: Web Service (needed for always-on)
- Start Command: `python3 start_workers.py`
- Plan: Starter ($7/month) - required for persistent schedulers

**Note**: APIs extracted to separate repositories for independent deployment

### Deprecated

#### Microservices Architecture
- `live-odds-worker/` - Consolidated into `workers/live_odds/`
- `historical-odds-worker/` - Consolidated into `workers/historical_odds/`
- `statistics-worker/` - Consolidated into `workers/odds_statistics/`

**Reason**: Cost optimization and simplified deployment for current scale

**Preserved**:
- All individual worker code maintained in consolidated structure
- Ability to split back into microservices if needed in future
- Documentation of microservices architecture in `MICROSERVICES_ARCHITECTURE.md`

---

## [1.0.0] - Initial Release

### Added
- **Live odds collection** with adaptive scheduling (10s-15min based on race proximity)
- **Historical odds backfill** from 2015 to present (2.4M+ records)
- **Statistics tracking** with JSON output for API consumption
- **Supabase integration** for PostgreSQL database
- **Racing API integration** with embedded odds parsing
- **Comprehensive logging** with structured output
- **Error handling** with graceful degradation
- **Render.com deployment** with auto-scaling

### Database Schema
- `ra_odds_live` (31 columns) - Current/upcoming race odds
- `ra_odds_historical` - Historical race results and final odds
- Unique constraint: `(race_id, horse_id, bookmaker_id)`

### Features
- Adaptive fetch intervals based on race proximity
- Embedded odds parsing from racecards (26 bookmakers per horse)
- Daily historical backfill at 1:00 AM UK time
- Statistics updates every 10 minutes
- Fixed odds only (no exchange data)
- UK & Ireland races only

---

## Versioning

**Current Version**: 1.2.0

**Version History**:
- **1.2.0** (Oct 9, 2025) - Change detection + Redis cache + Frontend fix
- **1.1.0** (Oct 6, 2025) - Architecture consolidation
- **1.0.0** - Initial production release

---

## Upgrade Guide

### From 1.1.0 to 1.2.0

**Environment Variables** (Add these):
```bash
# Redis Cache (optional - graceful degradation if not set)
UPSTASH_REDIS_REST_URL=https://wise-crab-11560.upstash.io
UPSTASH_REDIS_REST_TOKEN=<your_token>
```

**Dependencies** (Update requirements.txt):
```bash
pip install --upgrade -r requirements.txt
```

**Database** (No schema changes required):
- No migrations needed
- Existing data fully compatible

**Deployment**:
1. Add Redis environment variables to Render.com
2. Push to GitHub (auto-deploys)
3. Monitor logs for "change detection" and "cache invalidation" messages
4. Verify skip rate >60% after 1 hour

**Rollback** (if needed):
```bash
# Revert to previous version
git revert HEAD~3..HEAD  # Reverts last 3 commits
git push origin main

# Or disable new features via environment variables
DISABLE_CHANGE_DETECTION=true  # Falls back to upsert all
UPSTASH_REDIS_REST_URL=        # Disables cache invalidation
```

### From 1.0.0 to 1.1.0

**Breaking Changes**: None

**Deployment**:
- Change from 3 services to 1 service on Render.com
- Update service configuration to use `start_workers.py`
- Consolidate environment variables into single service
- Cost reduced from $21/month to $7/month

---

## Support

**Issues**: Report bugs at https://github.com/matthewbarber/DarkHorses-Odds-Workers/issues

**Documentation**:
- `README.md` - User-facing project documentation
- `CLAUDE.md` - Technical implementation details for AI assistants
- `OPERATIONS.md` - Monitoring and troubleshooting guide
- `sql/` - Database schema and migrations

**Monitoring**:
- Render.com Dashboard: https://dashboard.render.com/
- Service: `darkhorses-workers`
- Logs: Real-time streaming available in dashboard

---

**Maintained by**: Matthew Barber
**AI Assistance**: Claude Code (Sonnet 4.5)
**Repository**: DarkHorses-Odds-Workers
