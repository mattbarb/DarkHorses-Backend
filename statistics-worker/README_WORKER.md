# Statistics Worker

Background worker that generates analytics and statistics from odds data.

## Features

- **Every 10 Minutes**: Updates statistics continuously
- **JSON Export**: Saves statistics to JSON files in `output/` directory
- **Analytics**: Generates insights on odds movements, bookmakers, courses
- **Direct PostgreSQL**: Uses direct DB connection for complex queries

## Database

Reads from: `ra_odds_live` and `ra_odds_historical` tables

## Configuration

Copy `.env.example` to `.env` and configure:
- `DATABASE_URL` - PostgreSQL connection string (direct, not Supabase SDK)

## Running Locally

```bash
pip install -r requirements.txt

# One-time run
python3 update_stats.py --table all

# Continuous mode (for Render)
python3 update_stats.py --loop
```

## Deploy to Render.com

```bash
# Using render.yaml in this directory
render deploy
```

Service Type: Background Worker
Cost: $7/month (Starter plan required for always-on)

## Output

Statistics are saved to `output/*.json` files:
- `all_stats_latest.json` - Complete statistics
