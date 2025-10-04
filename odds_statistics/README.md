# Odds Data Pipeline Statistics Tracker

Comprehensive statistics tracking for the odds data pipeline, monitoring both `rb_odds_historical` and `ra_odds_live` tables.

## Features

- **Dual Table Tracking**: Monitor both historical and live odds tables
- **Comprehensive Statistics**:
  - Basic metrics (total records, date ranges)
  - Recent activity (last hour, 24h, 7 days)
  - Unique entities (races, horses, bookmakers)
  - Data quality metrics (NULL counts, completeness)
  - Distribution analysis (by date, country, track, bookmaker)
- **Multiple Output Formats**: Console (pretty tables) and JSON
- **Direct PostgreSQL Connection**: Fast, efficient queries
- **Production Ready**: Error handling, logging, connection management

## Installation

```bash
cd /Users/matthewbarber/Documents/GitHub/DarkHorses-Backend/odds_statistics

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Show all statistics in console (default)
python stats_tracker.py

# Show only historical table statistics
python stats_tracker.py --table historical

# Show only live odds table statistics
python stats_tracker.py --table live
```

### JSON Output

```bash
# Print JSON to console
python stats_tracker.py --format json

# Save JSON to file
python stats_tracker.py --format json --output stats.json

# Save specific table to JSON
python stats_tracker.py --table live --format json --output live_stats.json
```

### Examples

```bash
# Monitor live odds pipeline health
python stats_tracker.py --table live

# Export full report for analysis
python stats_tracker.py --format json --output reports/stats_$(date +%Y%m%d).json

# Quick check of recent activity
python stats_tracker.py --table live | grep "RECENT ACTIVITY" -A 5
```

## Statistics Collected

### rb_odds_historical

- **Basic Metrics**: Total records, date range, latest update
- **Recent Activity**: Records added (last hour, 24h, 7 days)
- **Unique Entities**: Horses, tracks, jockeys, trainers, countries
- **Records Per Date**: Last 7 days breakdown
- **Country Distribution**: Top 10 countries by volume
- **Track Distribution**: Top 10 tracks by volume
- **Data Quality**: NULL counts for critical fields
- **Odds Coverage**: Coverage percentages for different odds types

### ra_odds_live

- **Basic Metrics**: Total records, date ranges, latest fetch
- **Recent Activity**: Records fetched (last hour, 24h)
- **Unique Entities**: Races, horses, courses, bookmakers
- **Bookmaker Coverage**: Odds count, races/horses covered per bookmaker
- **Records Per Date**: Last 7 days breakdown with race/bookmaker counts
- **Course Distribution**: Top 20 courses by volume
- **Data Quality**: NULL counts for critical fields
- **Market Status**: Distribution of market statuses (OPEN/CLOSED/etc)

## Configuration

The tracker uses environment variables from `.env.local` or `.env` in the parent directory:

```bash
# Database connection
DATABASE_URL=postgresql://postgres:PASSWORD@db.amsjvmlaknnvppxsgpfk.supabase.co:5432/postgres
```

Configuration can be customized in `config.py`:
- `DEFAULT_DAYS_LOOKBACK`: Days to look back for date-based stats (default: 7)
- `DEFAULT_TOP_N_TRACKS`: Number of top tracks to show (default: 20)
- `DEFAULT_TOP_N_COUNTRIES`: Number of top countries to show (default: 10)

## Scheduling

### Cron (macOS/Linux)

```bash
# Run every hour and save to JSON
0 * * * * cd /path/to/odds_statistics && python3 stats_tracker.py --format json --output /path/to/logs/stats_$(date +\%Y\%m\%d_\%H00).json

# Run daily report at 9 AM
0 9 * * * cd /path/to/odds_statistics && python3 stats_tracker.py --format json --output /path/to/reports/daily_$(date +\%Y\%m\%d).json
```

### Manual Monitoring

```bash
# Create an alias for quick access
alias odds-stats='python3 /path/to/odds_statistics/stats_tracker.py'

# Then simply run:
odds-stats
odds-stats --table live
odds-stats --format json --output latest.json
```

## Output Examples

### Console Output

```
================================================================================
  ODDS DATA PIPELINE STATISTICS REPORT
================================================================================
  Timestamp: 2025-10-04T15:30:45.123456
================================================================================

┌──────────────────────────────────────────────────────────────────────────┐
│ TABLE: rb_odds_historical                                                  │
└──────────────────────────────────────────────────────────────────────────┘

📊 BASIC METRICS
Metric                    Value
----------------------  --------
Total Records            1,234,567
Earliest Race Date       2023-01-23
Latest Race Date         2025-10-04
Date Range (days)        1015
Latest Update            2025-10-04 14:25:30

📈 RECENT ACTIVITY
Period           Records Added
-------------  ---------------
Last Hour                1,245
Last 24 Hours           28,934
Last 7 Days            189,567

...
```

### JSON Output

```json
{
  "timestamp": "2025-10-04T15:30:45.123456",
  "rb_odds_historical": {
    "basic_metrics": {
      "total_records": 1234567,
      "earliest_race_date": "2023-01-23",
      "latest_race_date": "2025-10-04",
      "date_range_days": 1015,
      "latest_update": "2025-10-04T14:25:30"
    },
    ...
  },
  "ra_odds_live": {
    ...
  }
}
```

## Architecture

```
odds_statistics/
├── config.py                 # Configuration management
├── database.py              # PostgreSQL connection manager
├── stats_tracker.py         # Main entry point (CLI)
├── collectors/
│   ├── historical_collector.py  # rb_odds_historical stats
│   └── live_collector.py        # ra_odds_live stats
└── formatters/
    ├── console_formatter.py  # Terminal output
    └── json_formatter.py     # JSON output
```

## Troubleshooting

### Connection Issues

```bash
# Test database connection
python -c "from database import DatabaseConnection; from config import Config; db = DatabaseConnection(Config.DATABASE_URL); print('✅ Connected' if db.test_connection() else '❌ Failed')"
```

### Missing Dependencies

```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall
```

### Permission Errors

```bash
# Make script executable
chmod +x stats_tracker.py

# Run directly
./stats_tracker.py
```

## Development

### Adding New Statistics

1. Add query method to appropriate collector (`collectors/historical_collector.py` or `collectors/live_collector.py`)
2. Call method in `collect_all_stats()`
3. Add formatting in appropriate formatter (`formatters/console_formatter.py` or `formatters/json_formatter.py`)

### Adding New Output Format

1. Create new formatter in `formatters/` (e.g., `csv_formatter.py`)
2. Implement `format_stats(stats: Dict)` method
3. Import and use in `stats_tracker.py`

## License

Part of the DarkHorses-Backend racing odds data pipeline.
