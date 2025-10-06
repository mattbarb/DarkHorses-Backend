# Live Odds Worker

Background worker that collects live odds data from The Racing API for current and upcoming races.

## Features

- **Adaptive Scheduling**: Adjusts fetch frequency based on race proximity
  - 10 seconds when race imminent (<5 min)
  - 60 seconds when race soon (<30 min)
  - 5 minutes when race upcoming (<2 hours)
  - 15 minutes default check interval
- **Real-time Updates**: Tracks odds changes every 5 minutes
- **Stops at Race Start**: Automatically stops updating when race begins
- **26 Bookmakers**: Collects fixed odds from major bookmakers

## Database

Writes to: `ra_odds_live` table in Supabase

## Configuration

Copy `.env.example` to `.env` and configure:
- `RACING_API_USERNAME` - Racing API credentials
- `RACING_API_PASSWORD` - Racing API credentials
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service key

## Running Locally

```bash
pip install -r requirements.txt
python3 cron_live.py
```

## Deploy to Render.com

```bash
# Using render.yaml in this directory
render deploy
```

Service Type: Background Worker
Cost: $7/month (Starter plan required for always-on)
