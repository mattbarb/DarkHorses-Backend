# Race Name Implementation - Summary

## Problem Statement

The `ra_odds_historical` table was missing the `race_name` field (e.g., "THE RAY HAWTHORNE MEMORIAL AMATEUR"). This information was available in the Racing API but not being stored in the database.

## Investigation Results

✅ **Live Odds (`ra_odds_live`)**: Already has `race_name` column and captures it correctly
❌ **Historical Odds (`ra_odds_historical`)**: Missing `race_name` column entirely

### Root Cause Analysis

1. **Fetcher Layer** ✅ - `historical_odds_fetcher.py:254` DOES capture `race_name` from API
2. **Database Schema** ❌ - `ra_odds_historical` table DOES NOT have `race_name` column
3. **Schema Mapping** ❌ - `schema_mapping.py` DOES NOT include `race_name` in mapped records

**Conclusion**: The data was being fetched but dropped during database insertion due to missing column and mapping.

## Solution Implemented

### 1. Database Migration ✅
**File**: `sql/add_race_name_to_historical.sql`

```sql
ALTER TABLE ra_odds_historical ADD COLUMN race_name TEXT;
CREATE INDEX idx_ra_odds_historical_race_name ON ra_odds_historical (race_name);
```

### 2. Code Update ✅
**File**: `historical-odds-worker/schema_mapping.py:382`

Added one line to include race_name in the schema mapping:

```python
'race_name': combined_data.get('race_name'),  # NEW
```

### 3. Backfill Script ✅
**File**: `sql/backfill_race_names.py`

Intelligent backfill script that:
- Fetches records with NULL `race_name`
- Groups by unique race (date, track, time)
- Queries Racing API for race names
- Updates all matching records efficiently

## Implementation Status

| Component | Status | File | Action Required |
|-----------|--------|------|-----------------|
| Database Schema | ✅ Ready | `sql/add_race_name_to_historical.sql` | Run in Supabase SQL Editor |
| Code Changes | ✅ Ready | `historical-odds-worker/schema_mapping.py` | Deploy via git push |
| Backfill Script | ✅ Ready | `sql/backfill_race_names.py` | Run after migration + deploy |
| Documentation | ✅ Complete | `docs/RACE_NAME_FIX.md` | Reference guide available |
| Changelog | ✅ Updated | `CHANGELOG.md` | Version 1.3.0 documented |

## Deployment Plan

### Step 1: Database Migration (5 minutes)
```sql
-- Run in Supabase SQL Editor
-- Copy contents of sql/add_race_name_to_historical.sql
```

**Expected Result**: `race_name` column added to `ra_odds_historical` table

### Step 2: Code Deployment (5 minutes)
```bash
git add historical-odds-worker/schema_mapping.py
git add sql/add_race_name_to_historical.sql
git add sql/backfill_race_names.py
git add docs/RACE_NAME_FIX.md
git add docs/RACE_NAME_IMPLEMENTATION_SUMMARY.md
git add CHANGELOG.md
git commit -m "Add race_name field to historical odds table"
git push origin main
```

**Expected Result**: Render.com auto-deploys updated workers

### Step 3: Verify New Records (10 minutes)
```sql
-- Wait for one historical worker cycle, then check:
SELECT
    date_of_race,
    race_name,
    track,
    horse_name
FROM ra_odds_historical
WHERE created_at >= NOW() - INTERVAL '1 hour'
AND race_name IS NOT NULL
LIMIT 5;
```

**Expected Result**: New records have `race_name` populated

### Step 4: Run Backfill (4-8 hours)
```bash
# Test first with small batch
cd sql
python3 backfill_race_names.py --batch-size 1000 --max-races 100

# If successful, run full backfill
python3 backfill_race_names.py --batch-size 10000
```

**Expected Result**: Existing 2.4M records get `race_name` backfilled

## Impact Assessment

### Database Changes
- **New column**: `race_name TEXT` (~10MB storage)
- **New index**: `idx_ra_odds_historical_race_name` (~5MB storage)
- **Total storage increase**: ~15MB (negligible)

### API Usage
- **Backfill**: ~40K API calls (one-time)
- **Ongoing**: No additional API calls (data already fetched)
- **Rate limiting**: 0.2s delay between calls
- **Total time**: 4-8 hours (one-time backfill)

### Code Changes
- **Files modified**: 1 (schema_mapping.py)
- **Lines changed**: 1 (added race_name mapping)
- **Breaking changes**: None
- **Backward compatibility**: Full

### Performance Impact
- **New records**: No performance impact (field already fetched)
- **Backfill**: Runs asynchronously, no impact on workers
- **Query performance**: Index created for fast filtering

## Verification Queries

### Check Migration Success
```sql
-- Verify column exists
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'ra_odds_historical'
AND column_name = 'race_name';
```

### Check New Records
```sql
-- Verify new records have race_name
SELECT
    COUNT(*) as new_records,
    COUNT(race_name) as with_race_name,
    (COUNT(race_name)::float / COUNT(*) * 100)::numeric(5,2) as completion_pct
FROM ra_odds_historical
WHERE created_at >= NOW() - INTERVAL '24 hours';
```

### Check Backfill Progress
```sql
-- Overall completion
SELECT
    COUNT(*) as total_records,
    COUNT(race_name) as records_with_race_name,
    COUNT(*) - COUNT(race_name) as records_missing_race_name,
    (COUNT(race_name)::float / COUNT(*) * 100)::numeric(5,2) as completion_pct
FROM ra_odds_historical;
```

### Sample Race Names
```sql
-- View variety of race names
SELECT race_name, COUNT(*) as occurrences
FROM ra_odds_historical
WHERE race_name IS NOT NULL
GROUP BY race_name
ORDER BY occurrences DESC
LIMIT 20;
```

## Rollback Plan

If issues occur, rollback is straightforward:

### Rollback Code Changes
```bash
git revert HEAD
git push origin main
```

### Rollback Database (Optional)
```sql
-- Remove column (WARNING: data loss!)
ALTER TABLE ra_odds_historical DROP COLUMN race_name;
DROP INDEX IF EXISTS idx_ra_odds_historical_race_name;
```

**Note**: Database rollback is optional as the column being NULL causes no issues.

## Success Criteria

After full deployment and backfill:

- [x] `ra_odds_live` has `race_name` for all current races ✅ (already working)
- [ ] `ra_odds_historical` has `race_name` column (pending migration)
- [ ] All new historical records include `race_name` (pending code deploy)
- [ ] >95% of existing records backfilled with `race_name` (pending backfill)
- [ ] API queries can filter by race name: `WHERE race_name ILIKE '%stakes%'`

## Monitoring

### During Deployment
```bash
# Watch worker logs for new race_name values
tail -f /var/log/workers.log | grep "race_name"
```

### After Backfill
```sql
-- Daily progress check
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_records,
    COUNT(race_name) as with_race_name,
    (COUNT(race_name)::float / COUNT(*) * 100)::numeric(5,2) as completion_pct
FROM ra_odds_historical
GROUP BY DATE(created_at)
ORDER BY date DESC
LIMIT 7;
```

## Cost Analysis

| Item | Cost | Frequency | Total |
|------|------|-----------|-------|
| Database storage | $0.125/GB | One-time | ~$0.002 (15MB) |
| API calls | Included | One-time | $0 (within limits) |
| Compute time | $0.01/hour | One-time | ~$0.08 (8 hours) |
| **Total** | | | **~$0.10** |

**Conclusion**: Negligible cost for significant data quality improvement.

## Next Steps

1. ✅ Review this summary
2. ⏳ Run database migration in Supabase
3. ⏳ Deploy code changes via git push
4. ⏳ Verify new records include race_name
5. ⏳ Run backfill script for existing data
6. ⏳ Update API documentation to include race_name field
7. ⏳ Notify frontend team that race_name is now available

## Files Reference

- **Migration**: `sql/add_race_name_to_historical.sql`
- **Code Change**: `historical-odds-worker/schema_mapping.py:382`
- **Backfill**: `sql/backfill_race_names.py`
- **Guide**: `docs/RACE_NAME_FIX.md`
- **Summary**: `docs/RACE_NAME_IMPLEMENTATION_SUMMARY.md` (this file)
- **Changelog**: `CHANGELOG.md` (version 1.3.0)

## Questions or Issues?

Refer to `docs/RACE_NAME_FIX.md` for detailed troubleshooting and deployment instructions.
