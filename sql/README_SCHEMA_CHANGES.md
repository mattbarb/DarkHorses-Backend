# Schema Changes: Removed Exchange Odds Columns

## Date
2025-10-04

## Summary
Removed 7 unused columns from `ra_odds_live` table that were designed for exchange odds data (Betfair, Smarkets, etc.) but were never populated because the Racing API doesn't provide this data.

## Motivation
- The Racing API `/racecards/pro` endpoint only provides **fixed odds** from traditional bookmakers
- Exchange odds (back/lay prices, market depth) are **not available** in the racecard response
- The deprecated `/odds/{race_id}/{horse_id}` endpoint that might have provided exchange data returns 404
- These columns remained NULL for 100% of records, wasting database space and causing confusion

## Columns Removed

| Column Name | Data Type | Purpose |
|-------------|-----------|---------|
| `back_price` | NUMERIC(10,3) | Exchange back price (not available) |
| `lay_price` | NUMERIC(10,3) | Exchange lay price (not available) |
| `back_size` | NUMERIC(12,2) | Available liquidity to back (not available) |
| `lay_size` | NUMERIC(12,2) | Available liquidity to lay (not available) |
| `back_prices` | JSONB | Top 3 back prices (not available) |
| `lay_prices` | JSONB | Top 3 lay prices (not available) |
| `total_matched` | NUMERIC(15,2) | Total matched on exchange (not available) |

## Columns Modified

| Column Name | Change | Reason |
|-------------|--------|--------|
| `bookmaker_type` | Added DEFAULT 'fixed' | All bookmakers are fixed odds type |

## How to Apply Migration

### Option 1: Run Migration Script (Recommended)
```sql
-- In Supabase SQL Editor
\i migrate_remove_exchange_columns.sql
```

### Option 2: Drop and Recreate (Nuclear Option)
**⚠️ WARNING: This will delete all data!**
```sql
-- Only use if you're okay losing all data in ra_odds_live
\i create_ra_odds_live.sql
```

### Option 3: Manual Commands
```sql
BEGIN;

ALTER TABLE ra_odds_live
DROP COLUMN IF EXISTS back_price,
DROP COLUMN IF EXISTS lay_price,
DROP COLUMN IF EXISTS back_size,
DROP COLUMN IF EXISTS lay_size,
DROP COLUMN IF EXISTS back_prices,
DROP COLUMN IF EXISTS lay_prices,
DROP COLUMN IF EXISTS total_matched;

ALTER TABLE ra_odds_live
ALTER COLUMN bookmaker_type SET DEFAULT 'fixed';

COMMIT;
```

## Code Changes

### Files Modified
1. **`sql/create_ra_odds_live.sql`** - Updated schema definition
2. **`live_odds/live_odds_fetcher.py`** - Removed exchange fields from OddsData dataclass
3. **`live_odds/live_odds_client.py`** - Removed exchange column mappings from _prepare_live_record()
4. **`live_odds/cron_live.py`** - Removed exchange fields from record dict

### Before/After Schema Comparison

**Before (38 columns):**
- 31 populated columns
- 7 NULL exchange columns (never populated)

**After (31 columns):**
- 31 populated columns
- 0 NULL columns
- 100% data utilization

## Impact

### Positive
✅ Reduced table size (7 fewer columns per row)
✅ Simplified codebase (removed unused code paths)
✅ Clearer data model (only includes available data)
✅ Faster queries (less data to scan)
✅ No more confusion about why exchange columns are NULL

### Neutral
➖ Cannot add exchange odds without schema change (but we didn't have them anyway)
➖ Breaking change if external queries reference deleted columns (unlikely)

### Negative
❌ None - these columns were never populated

## Rollback Plan

If you need to restore exchange columns:

```sql
ALTER TABLE ra_odds_live
ADD COLUMN back_price NUMERIC(10,3),
ADD COLUMN lay_price NUMERIC(10,3),
ADD COLUMN back_size NUMERIC(12,2),
ADD COLUMN lay_size NUMERIC(12,2),
ADD COLUMN back_prices JSONB,
ADD COLUMN lay_prices JSONB,
ADD COLUMN total_matched NUMERIC(15,2);
```

## Future Considerations

If Racing API adds exchange odds support in the future:
1. Re-add columns using ALTER TABLE commands above
2. Update OddsData dataclass to include exchange fields
3. Update parse_embedded_odds() to extract exchange data
4. Update _prepare_live_record() to map exchange fields

## Testing

After applying migration:

```sql
-- Verify columns were removed
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'ra_odds_live'
ORDER BY ordinal_position;

-- Should show 31 columns (not 38)
SELECT COUNT(*) as column_count
FROM information_schema.columns
WHERE table_name = 'ra_odds_live';

-- Verify bookmaker_type has default
SELECT column_default
FROM information_schema.columns
WHERE table_name = 'ra_odds_live'
AND column_name = 'bookmaker_type';
-- Should return: 'fixed'::text
```

## References

- **Audit Report**: See comprehensive column audit in previous session
- **API Documentation**: Racing API doesn't provide exchange odds in `/racecards/pro`
- **Issue**: All 7 exchange columns remained NULL for 100% of records
