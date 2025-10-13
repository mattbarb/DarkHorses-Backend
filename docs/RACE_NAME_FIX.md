# Race Name Missing from Historical Odds - Fix Implementation

## Problem Identified

The `ra_odds_historical` table was missing the `race_name` field (e.g., "THE RAY HAWTHORNE MEMORIAL AMATEUR"), even though the Racing API provides this data and the `ra_odds_live` table already has it.

**Root Cause:**
1. The historical odds fetcher **WAS** capturing `race_name` from the API
2. The database schema **DID NOT** have a `race_name` column
3. The schema mapper **WAS NOT** including `race_name` in the mapped records

## Solution Implemented

### 1. Database Schema Update ✅

**File:** `sql/add_race_name_to_historical.sql`

Adds `race_name` column to `ra_odds_historical` table with index.

### 2. Code Updates ✅

**File:** `historical-odds-worker/schema_mapping.py:382`

Added `race_name` to the schema mapping:

```python
# Race details
'race_name': combined_data.get('race_name'),  # NEW LINE
'going': combined_data.get('going'),
'race_type': combined_data.get('race_type'),
```

The fetcher was already capturing it from the API (line 254 in `historical_odds_fetcher.py`), so no changes needed there.

### 3. Backfill Script ✅

**File:** `sql/backfill_race_names.py`

Intelligent backfill script that:
- Finds all records with NULL `race_name`
- Groups by unique race (date, track, time)
- Fetches race names from Racing API results endpoint
- Updates all matching records efficiently

## Deployment Steps

### Step 1: Run Database Migration

Execute in Supabase SQL Editor:

```bash
# Copy the contents of:
sql/add_race_name_to_historical.sql
```

This will:
- Add `race_name TEXT` column
- Create index for performance
- Keep existing data (all NULL initially)

### Step 2: Deploy Code Changes

The code changes are already committed and will deploy automatically via GitHub:

```bash
git add historical-odds-worker/schema_mapping.py
git commit -m "Add race_name to historical odds schema mapping"
git push origin main
```

Render.com will auto-deploy the updated workers.

### Step 3: Test on Sample Data (Optional)

Test the backfill script in dry-run mode:

```bash
cd sql
python3 backfill_race_names.py --dry-run --max-races 10
```

This shows what would be done without making changes.

### Step 4: Run Backfill Script

**IMPORTANT:** This should be run AFTER the database migration is complete.

```bash
cd sql

# Test with small batch first (100 races)
python3 backfill_race_names.py --batch-size 1000 --max-races 100

# Check results in database
# If successful, run full backfill:

python3 backfill_race_names.py --batch-size 10000
```

**Backfill Process:**
1. Fetches up to 10,000 records missing `race_name`
2. Groups them by unique race (typically ~100-200 races per 10K records)
3. Queries Racing API once per unique race
4. Updates all records for that race in batches of 100

**Performance Estimate:**
- ~10K records = ~150 unique races
- ~150 API calls (0.2s delay each) = ~30 seconds
- Total time: ~1-2 minutes per 10K records
- 2.4M records ≈ 240 batches ≈ 4-8 hours total

**Rate Limiting:**
- Script includes 0.2s delay between API calls
- Handles 429 (rate limit) errors gracefully
- Safe to run in production

### Step 5: Verify Results

Check that race names are being populated:

```sql
-- Check backfill progress
SELECT
    COUNT(*) as total_records,
    COUNT(race_name) as records_with_race_name,
    COUNT(*) - COUNT(race_name) as records_missing_race_name,
    (COUNT(race_name)::float / COUNT(*) * 100)::numeric(5,2) as completion_percentage
FROM ra_odds_historical;

-- View sample race names
SELECT
    date_of_race,
    track,
    race_time,
    race_name,
    horse_name
FROM ra_odds_historical
WHERE race_name IS NOT NULL
ORDER BY date_of_race DESC
LIMIT 20;

-- Check for specific race
SELECT DISTINCT race_name
FROM ra_odds_historical
WHERE race_name ILIKE '%HAWTHORNE%';
```

## Future Data Collection

### Live Odds ✅
Already includes `race_name` - no changes needed.

### Historical Odds ✅
Now includes `race_name` for all new records after deployment.

## Monitoring

After deployment, verify new historical records are getting `race_name`:

```sql
-- Check records created after deployment
SELECT
    COUNT(*) as new_records,
    COUNT(race_name) as records_with_name
FROM ra_odds_historical
WHERE created_at >= '2025-01-XX'  -- Replace with deployment date
GROUP BY date_of_race
ORDER BY date_of_race DESC
LIMIT 10;
```

Should show 100% of new records have `race_name`.

## Rollback Plan

If issues occur, the changes are safe to rollback:

```sql
-- Remove the column (data loss!)
ALTER TABLE ra_odds_historical DROP COLUMN race_name;

-- Or keep the column but revert code:
git revert <commit-hash>
git push origin main
```

## Files Changed

1. ✅ `sql/add_race_name_to_historical.sql` - Database migration
2. ✅ `historical-odds-worker/schema_mapping.py` - Add race_name to mapping
3. ✅ `sql/backfill_race_names.py` - Backfill script for existing records
4. ✅ `docs/RACE_NAME_FIX.md` - This deployment guide

## Testing Results

**Expected after deployment:**
- ✅ New live odds records: Already have `race_name`
- ✅ New historical records: Will have `race_name` (after code deploy)
- ⏳ Existing historical records: Will have `race_name` (after backfill)

## Cost Estimate

**API Usage:**
- ~2.4M records ≈ ~40K unique races
- 40K API calls to results endpoint
- Racing API allows ~100K calls/month
- Well within limits

**Database:**
- New column: ~10MB additional storage
- Index: ~5MB
- Negligible cost increase

**Compute:**
- Backfill script: 4-8 hours one-time
- Can run locally or on Render (free instance)

## Success Criteria

After full deployment and backfill:

1. ✅ `ra_odds_live` has `race_name` for all current races
2. ✅ `ra_odds_historical` has `race_name` column
3. ✅ All new historical records include `race_name`
4. ✅ >95% of existing records backfilled with `race_name`
5. ✅ API queries can filter by race name: `WHERE race_name ILIKE '%stakes%'`

## Next Steps

1. Run database migration in Supabase
2. Deploy code changes (auto-deploy on push)
3. Test backfill script with small batch
4. Run full backfill (can run in background)
5. Verify results with SQL queries
6. Update API documentation to include `race_name` field
