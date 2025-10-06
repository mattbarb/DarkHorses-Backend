# Historical Odds Service

Continuous backfill of historical horse racing odds from 2015 to current date with daily updates.

## Purpose

1. **Complete Backfill**: Fetches all historical data from 2015 to current date
2. **Daily Updates**: Runs at 1:00 AM UK time to fetch recent completed races
3. **Continuous Updates**: Keeps the database current with no gaps in data

## Scheduling

### Daily Execution
- Runs at **1:00 AM UK time** (Europe/London timezone)
- Fetches previous day's completed races
- Processes up to 10 missing dates per run for backfill
- Automatic retry with 1-hour delay on errors

### Backfill Strategy
- Starts from January 1, 2015
- Continues to current date (yesterday)
- Identifies and fills all missing dates
- Processes 50 dates per cycle to avoid API overload
- Runs continuously until 95% complete
- Switches to maintenance mode when backfill complete

## Features

- Fetches final odds at race start time
- Captures odds from all available bookmakers
- Stores in Supabase database (`ra_odds_historical` table)
- Automatic course name mapping
- Comprehensive error handling and logging
- Resume capability for interrupted backfills

## Configuration

Set these environment variables in Render dashboard:

```bash
RACING_API_USERNAME=<your_username>
RACING_API_PASSWORD=<your_password>
SUPABASE_URL=<your_supabase_url>
SUPABASE_SERVICE_KEY=<your_service_key>
LOG_LEVEL=INFO  # Optional
BACKFILL_START_YEAR=2015  # Optional, defaults to 2015
```

## Files

- `cron_historical.py` - Main scheduler (1 AM daily + backfill)
- `historical_odds_fetcher.py` - Fetches historical odds from Racing API
- `historical_odds_client.py` - Stores odds in Supabase
- `backfill_historical.py` - Backfill logic and missing date detection
- `schema_mapping.py` - Maps API data to database schema
- `course_lookup.py` - Course name standardization
- `create_ra_odds_historical.sql` - Database schema
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration

## Deployment

### Render.com (Recommended)

```bash
# Deploy both services from root:
cd /path/to/production
render deploy
```

The service will:
1. Start at deployment
2. Wait until 1:00 AM UK time
3. Run daily job (yesterday + backfill chunk)
4. Repeat daily

### Manual Testing

```bash
# Test locally
cd historical
pip install -r requirements.txt

# Run once (for testing)
python3 cron_historical.py --once

# Run continuously
python3 cron_historical.py

# Run backfill only
python3 backfill_historical.py --start-year 2015
```

## Database Schema

Stores odds in `ra_odds_historical` table:

```sql
- race_id: Race identifier
- horse_id: Horse identifier
- race_date: Race date
- course: Standardized track name
- course_id: Track identifier
- off_time: Race start time
- race_name: Race name
- race_class: Classification
- race_type: Flat/Jump/etc
- distance: Distance in meters
- going: Track conditions
- horse_name: Horse name
- jockey: Jockey name
- trainer: Trainer name
- bookmaker_id: Bookmaker identifier
- bookmaker_name: Display name
- bookmaker_type: 'exchange' or 'fixed'
- odds: Decimal odds
- sp: Starting price (if available)
- position: Final position
- fetched_at: Timestamp
- source: 'racing_api'
```

## Daily Job Process

Each day at 1 AM:

1. **Fetch Yesterday**
   - Get completed races from previous day
   - Fetch final odds for each horse
   - Store in database

2. **Backfill Chunk**
   - Query database for missing dates
   - Process up to 10 oldest missing dates
   - Continue until historical data complete

3. **Logging**
   - Record statistics
   - Log any errors
   - Calculate next run time

## Monitoring

Check logs in Render dashboard or local `cron_historical.log`:

```bash
tail -f cron_historical.log
```

Look for:
- Daily job execution time
- Number of races/odds processed
- Backfill progress (dates remaining)
- Any errors or API issues

## Backfill Progress

Monitor backfill completion:

```sql
-- Check date coverage
SELECT
    MIN(race_date) as earliest_date,
    MAX(race_date) as latest_date,
    COUNT(DISTINCT race_date) as dates_with_data
FROM ra_odds_historical;

-- Find missing dates
SELECT generate_series(
    '2015-01-01'::date,
    CURRENT_DATE,
    '1 day'::interval
)::date as missing_date
EXCEPT
SELECT DISTINCT race_date
FROM ra_odds_historical
ORDER BY missing_date;
```

## Troubleshooting

**No data being stored:**
- Check API credentials
- Verify Supabase connection
- Check Racing API has results for date
- Review logs for errors

**Backfill not progressing:**
- Check for API rate limits
- Verify date range configuration
- Look for repeated errors in logs
- Check database connectivity

**Incorrect times:**
- Service uses UK timezone (Europe/London)
- Check server timezone settings
- Verify race times in database

**Course names not matching:**
- Course lookup maps Racing API names to standard names
- Check `course_lookup.py` for mappings
- Add missing courses if needed

## Development

Run specific components:

```python
# Fetch one date
from historical_odds_fetcher import HistoricalOddsFetcher
fetcher = HistoricalOddsFetcher()
races = fetcher.fetch_results('2025-09-29')

# Process backfill
from backfill_historical import HistoricalBackfill
backfill = HistoricalBackfill(start_year=2015)
stats = backfill.process_missing_dates(limit=5)

# Test scheduler once
from cron_historical import HistoricalOddsScheduler
scheduler = HistoricalOddsScheduler()
scheduler.run_once()
```

## Support

For issues or questions, check:
- Render deployment logs
- Application logs (`cron_historical.log`)
- Racing API documentation
- Supabase connection status
- Database schema and queries
