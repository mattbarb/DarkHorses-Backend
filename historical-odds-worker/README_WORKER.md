# Historical Odds Worker

Background worker that backfills historical race results and final odds from The Racing API.

## Features

- **Daily Backfill**: Runs daily at 1:00 AM UK time
- **Historical Data**: Fetches race results from 2015 to present
- **Final Odds**: Captures closing odds and finishing positions
- **Smart Resume**: Skips already completed dates

## Database

Writes to: `ra_odds_historical` table in Supabase

## Configuration

Copy `.env.example` to `.env` and configure:
- `RACING_API_USERNAME` - Racing API credentials
- `RACING_API_PASSWORD` - Racing API credentials
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service key

## Running Locally

```bash
pip install -r requirements.txt
python3 cron_historical.py
```

## Deploy to Render.com

```bash
# Using render.yaml in this directory
render deploy
```

Service Type: Background Worker
Cost: $7/month (Starter plan required for always-on)

## Manual Backfill

```bash
python3 backfill_historical.py --start-year 2015 --end-year 2024
```
