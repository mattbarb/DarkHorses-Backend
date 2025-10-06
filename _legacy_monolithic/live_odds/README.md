# Live Odds Service

Smart scheduler for real-time horse racing odds from The Racing API.

## Purpose

Fetches live odds from multiple bookmakers for today's and tomorrow's races with intelligent scheduling based on race proximity.

## Scheduling Strategy

The service uses **smart scheduling** that adjusts fetch frequency based on how close races are:

| Time Until Race | Fetch Interval | Reason |
|----------------|----------------|--------|
| ≤ 5 minutes | Every 10 seconds | Imminent - capture final odds movements |
| ≤ 30 minutes | Every 1 minute | Soon - frequent updates |
| ≤ 2 hours | Every 5 minutes | Upcoming - regular monitoring |
| > 2 hours | Every 15 minutes | Check for new races |

## Features

- Continuous operation with adaptive intervals
- Fetches odds from all available bookmakers
- Stores odds in Supabase database (`ra_odds_live` table)
- Automatic error recovery with exponential backoff
- Comprehensive logging
- Stops after 5 consecutive errors for safety

## Configuration

Set these environment variables in Render dashboard:

```bash
RACING_API_USERNAME=<your_username>
RACING_API_PASSWORD=<your_password>
SUPABASE_URL=<your_supabase_url>
SUPABASE_SERVICE_KEY=<your_service_key>
LOG_LEVEL=INFO  # Optional, defaults to INFO
```

## Files

- `cron_live.py` - Main scheduler with smart interval logic
- `live_odds_fetcher.py` - Fetches odds from Racing API
- `live_odds_client.py` - Stores odds in Supabase
- `live_odds_scheduler.py` - Alternative scheduler implementation
- `create_ra_odds_live.sql` - Database schema
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration

## Deployment

### Render.com (Recommended)

```bash
# Deploy both services from root:
cd /path/to/production
render deploy
```

The service will start automatically and run continuously.

### Manual Testing

```bash
# Test locally
cd live_odds
pip install -r requirements.txt
python3 cron_live.py
```

## Database Schema

Stores odds in `ra_odds_live` table:

```sql
- race_id: Race identifier
- horse_id: Horse identifier
- race_date: Race date
- course: Track name
- off_time: Scheduled start time
- race_name: Race name
- horse_name: Horse name
- bookmaker_id: Bookmaker identifier
- bookmaker_name: Display name
- bookmaker_type: 'exchange' or 'fixed'
- odds: Decimal odds
- back_prices: JSON array (exchanges)
- lay_prices: JSON array (exchanges)
- fetched_at: Timestamp
- source: 'racing_api'
```

## Monitoring

Check logs in Render dashboard or local `cron_live.log`:

```bash
tail -f cron_live.log
```

Look for:
- Interval adjustments based on race proximity
- Number of races/horses/odds processed per cycle
- Any errors or API issues

## Troubleshooting

**No odds being stored:**
- Check API credentials are set correctly
- Verify races exist for today/tomorrow
- Check Racing API status

**High error rate:**
- Service stops after 5 consecutive errors
- Check API rate limits
- Verify network connectivity

**Incorrect intervals:**
- Verify system timezone
- Check race times in database
- Review logs for race proximity calculations

## Development

Run in single-execution mode for testing:

```python
from cron_live import LiveOddsScheduler

scheduler = LiveOddsScheduler()
scheduler.run_fetch_cycle()  # Run once
```

## Support

For issues or questions, check:
- Render deployment logs
- Application logs (`cron_live.log`)
- Racing API documentation
- Supabase connection status
