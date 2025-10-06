# DarkHorses Odds API

FastAPI web service providing REST API access to live odds, historical odds, and statistics.

## Features

- **Live Odds Endpoints**: Query current race odds with filters
- **Historical Odds**: Access past race data
- **Statistics**: View analytics on odds movements
- **Dashboard UI**: Kanban-style dashboard at `/`
- **Swagger Docs**: API documentation at `/docs`

## Endpoints

### Core
- `GET /` - Dashboard UI
- `GET /health` - Health check
- `GET /docs` - Swagger documentation

### Live Odds
- `GET /api/live-odds` - Query live odds (filters: race_date, course, bookmaker)
- `GET /api/live-odds/upcoming-races` - Races in next 24 hours

### Historical Odds
- `GET /api/historical-odds` - Historical odds (filters: year, course, race_date)

### Statistics
- `GET /api/statistics` - Latest statistics
- `GET /api/bookmakers` - List of bookmakers
- `GET /api/courses` - List of courses

## Configuration

Copy `.env.example` to `.env` and configure:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service key
- `DATABASE_URL` - PostgreSQL connection for queries

## Running Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Visit: http://localhost:8000

## Deploy to Render.com

```bash
# Using render.yaml in this directory
render deploy
```

Service Type: Web Service
Cost: $7/month (Starter) or Free tier

## Database Tables

Reads from:
- `ra_odds_live` - Current race odds
- `ra_odds_historical` - Historical race data
- `ra_odds_statistics` - Analytics data
