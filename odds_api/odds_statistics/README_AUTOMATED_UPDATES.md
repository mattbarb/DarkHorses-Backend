# Automated Statistics Updates

## Overview

The odds statistics system automatically updates after each successful fetch cycle from both the live odds and historical odds schedulers. Statistics are saved to JSON files for monitoring and analysis.

## How It Works

### Automatic Updates

Statistics are automatically collected and saved when:

1. **Live Odds Scheduler** (`live_odds/cron_live.py`)
   - Triggers after successful fetch cycle
   - Only updates when `odds_stored > 0`
   - Saves to `odds_statistics/output/live_stats_latest.json`

2. **Historical Odds Scheduler** (`historical_odds/cron_historical.py`)
   - Triggers after daily fetch cycles
   - Triggers after backfill operations
   - Only updates when records are successfully stored
   - Saves to `odds_statistics/output/historical_stats_latest.json`

### Output Location

All statistics JSON files are saved to:
```
/Users/matthewbarber/Documents/GitHub/DarkHorses-Backend/odds_statistics/output/
```

Files generated:
- `live_stats_latest.json` - Latest statistics for ra_odds_live table
- `historical_stats_latest.json` - Latest statistics for rb_odds_historical table
- `all_stats_latest.json` - Combined statistics (when running manually)

## Manual Updates

### Update Single Table

```bash
cd /Users/matthewbarber/Documents/GitHub/DarkHorses-Backend/odds_statistics

# Update live odds statistics
python3 update_stats.py --table live

# Update historical odds statistics
python3 update_stats.py --table historical
```

### Update All Tables

```bash
python3 update_stats.py --table all
```

### Skip File Save

```bash
python3 update_stats.py --table live --no-save
```

## Using the Full CLI

For more detailed statistics and console output:

```bash
cd /Users/matthewbarber/Documents/GitHub/DarkHorses-Backend/odds_statistics

# View live statistics in console
python3 stats_tracker.py --table live --format console

# Save historical statistics to JSON
python3 stats_tracker.py --table historical --format json

# Get both tables with console output
python3 stats_tracker.py --table all --format console
```

## Statistics Collected

### For ra_odds_live:
- Basic metrics (total records, date ranges)
- Recent activity (24h, 7d, 30d)
- Unique entities (races, horses, bookmakers)
- Bookmaker coverage
- Records per date
- Course distribution
- Data quality metrics
- Market status breakdown

### For rb_odds_historical:
- Basic metrics (total records, date ranges)
- Records per year/month
- Unique entities (races, horses, bookmakers)
- Bookmaker coverage over time
- Data quality metrics
- Course distribution

## Monitoring

### Check Latest Statistics

```bash
# View latest live stats
cat odds_statistics/output/live_stats_latest.json | jq .

# View latest historical stats
cat odds_statistics/output/historical_stats_latest.json | jq .

# Check file timestamps
ls -lah odds_statistics/output/
```

### Scheduler Logs

Statistics updates are logged in the scheduler output:

```
📊 Updating live odds statistics...
✅ Statistics updated successfully
📄 Statistics saved to /Users/matthewbarber/Documents/GitHub/DarkHorses-Backend/odds_statistics/output/live_stats_latest.json
```

## Error Handling

If statistics updates fail:
- Schedulers continue running (non-blocking)
- Error is logged with warning level
- Main fetch cycle is NOT affected

## Testing

Run the test suite to verify the statistics system:

```bash
cd /Users/matthewbarber/Documents/GitHub/DarkHorses-Backend/odds_statistics
python3 test_tracker.py
```

Expected output:
```
✅ PASS - Imports
✅ PASS - Configuration
✅ PASS - Database
```

## Integration Points

### Live Odds Integration
File: `live_odds/cron_live.py`
- Lines 26-36: Import statistics updater
- Lines 471-478: Update after successful fetch

### Historical Odds Integration
File: `historical_odds/cron_historical.py`
- Lines 32-40: Import statistics updater
- Lines 217-224: Update after daily fetch
- Lines 328-335: Update after backfill

## Database Connection

### Important Note on Connection Methods

The statistics tracker uses **direct PostgreSQL connection** for read-only queries because:
- Supabase client doesn't support complex aggregation queries (COUNT DISTINCT, GROUP BY, etc.)
- Statistics require raw SQL for efficient data analysis
- This is **read-only** - no writes to the database

The main data pipeline (live_odds, historical_odds) uses **Supabase client** for:
- All write operations (INSERT, UPDATE, UPSERT)
- Standard table operations

### Environment Variables Required

In your `.env` or `.env.local` file:
```bash
# For statistics tracker (read-only)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.amsjvmlaknnvppxsgpfk.supabase.co:5432/postgres

# For main data pipeline (Supabase client)
SUPABASE_URL=https://amsjvmlaknnvppxsgpfk.supabase.co
SUPABASE_SERVICE_KEY=your_service_key_here
```

## Troubleshooting

### Statistics Not Updating

1. Check if module is imported successfully:
   ```
   grep "Statistics updater imported" live_odds/logs/cron_live.log
   ```

2. Verify DATABASE_URL in `.env`:
   ```
   DATABASE_URL=postgresql://postgres:...
   ```

3. Check output directory exists:
   ```
   ls -la odds_statistics/output/
   ```

4. Run manual update to see detailed errors:
   ```
   python3 odds_statistics/update_stats.py --table live
   ```

### Module Import Errors

If statistics module fails to import, schedulers will:
- Log warning message
- Continue running normally
- Statistics updates will be skipped

This ensures the main data pipeline is never blocked by statistics issues.
