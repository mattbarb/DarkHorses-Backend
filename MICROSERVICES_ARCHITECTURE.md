# DarkHorses Backend - Microservices Architecture

## Overview

The DarkHorses backend has been restructured from a monolithic application into a microservices architecture with two separate services:

1. **Workers Service** - Background data collection (no HTTP server)
2. **API Service** - Read-only HTTP API and dashboard UI

Both services connect to the same Supabase PostgreSQL database. Workers write data, API reads data.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Supabase PostgreSQL                     │
│  Tables: ra_odds_live, ra_odds_historical, ra_bookmakers    │
└─────────────────────────────────────────────────────────────┘
           ▲                                    ▲
           │ WRITE                              │ READ
           │                                    │
┌──────────┴──────────┐              ┌─────────┴──────────┐
│  Workers Service    │              │   API Service      │
│                     │              │                    │
│  - Live Odds        │              │  - FastAPI Server  │
│  - Historical Odds  │              │  - Dashboard UI    │
│  - Statistics       │              │  - Read Endpoints  │
│                     │              │                    │
│  NO HTTP SERVER     │              │  Port 8000         │
└─────────────────────┘              └────────────────────┘
```

## Directory Structure

```
DarkHorses-Backend/
│
├── workers/                      # Background Data Collection Service
│   ├── start_workers.py          # Entry point (no HTTP server)
│   ├── scheduler.py              # Consolidated scheduler
│   ├── live_odds/                # Live odds fetching
│   ├── historical_odds/          # Historical odds fetching
│   ├── odds_statistics/          # Statistics collection
│   ├── requirements.txt          # Worker dependencies
│   └── logs/
│       └── scheduler_status.json # Written by workers, read by API
│
├── api/                          # Read-Only API Service
│   ├── main.py                   # FastAPI application
│   ├── static/                   # Dashboard UI
│   │   └── index.html
│   ├── requirements.txt          # API dependencies
│   └── logs/
│
├── _legacy_monolithic/           # OLD monolithic service (archived)
│   ├── README_LEGACY.md          # Rollback instructions
│   └── ... (kept for reference, not deployed)
│
├── render.yaml                   # Render.com deployment config
├── MICROSERVICES_ARCHITECTURE.md # This file
└── sql/                          # Database schemas
```

## Service Details

### Workers Service

**Purpose**: Continuous data collection from Racing API to Supabase

**Components**:
- Live Odds Scheduler: Adaptive intervals (10s to 15min based on race proximity)
- Historical Odds Scheduler: Daily at 1:00 AM UK time
- Statistics Updater: Every 10 minutes

**Entry Point**: `workers/start_workers.py`

**No HTTP Server**: This service does not expose any HTTP endpoints

**Status Updates**: Writes status to `workers/logs/scheduler_status.json` for API monitoring

**Dependencies**:
```
python-dotenv==1.0.0
supabase==2.0.3
pydantic==2.5.0
schedule==1.2.0
psycopg2-binary==2.9.9
```

**Environment Variables**:
```
RACING_API_USERNAME
RACING_API_PASSWORD
SUPABASE_URL
SUPABASE_SERVICE_KEY
DATABASE_URL
LOG_LEVEL=INFO
```

### API Service

**Purpose**: Read-only HTTP API and dashboard UI

**Components**:
- FastAPI application with read-only endpoints
- Dashboard UI (Kanban-style race cards)
- Statistics viewer
- Bookmaker and course listings

**Entry Point**: `api/main.py` via `uvicorn main:app`

**Port**: 8000 (configurable via PORT env var)

**Key Endpoints**:
- `GET /` - Dashboard UI
- `GET /health` - Health check
- `GET /api/live-odds` - Query live odds
- `GET /api/live-odds/races-by-stage` - Race cards grouped by stage
- `GET /api/historical-odds` - Query historical odds
- `GET /api/statistics` - View statistics
- `GET /api/scheduler-status` - Read worker status (from JSON file)
- `GET /api/bookmakers` - List bookmakers
- `GET /api/courses` - List courses

**Removed Endpoints** (worker-specific):
- `POST /api/statistics/refresh` - Now handled by workers
- `GET /api/scheduler-health` - Thread checking (not applicable)

**Dependencies**:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
supabase==2.0.3
pydantic==2.5.0
psycopg2-binary==2.9.9
```

**Environment Variables**:
```
SUPABASE_URL
SUPABASE_SERVICE_KEY
DATABASE_URL
LOG_LEVEL=INFO
PORT=8000
```

## Communication Between Services

**Database**: Both services share the same Supabase PostgreSQL database
- Workers WRITE to: `ra_odds_live`, `ra_odds_historical`, `ra_odds_statistics`
- API READS from: All tables

**Status File**: Workers write scheduler status to JSON file
- Workers write: `workers/logs/scheduler_status.json`
- API reads: `../workers/logs/scheduler_status.json` (via `/api/scheduler-status` endpoint)

**No Direct Communication**: Services do not communicate via HTTP/RPC - all communication is via database

## Deployment

### Render.com Configuration

The `render.yaml` file defines both services:

**Workers Service**:
```yaml
- type: web
  name: darkhorses-workers
  plan: starter  # Must be always-on
  rootDir: workers
  buildCommand: pip install -r requirements.txt
  startCommand: python3 start_workers.py
```

**API Service**:
```yaml
- type: web
  name: darkhorses-api
  plan: starter
  rootDir: api
  buildCommand: pip install -r requirements.txt
  startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
  healthCheckPath: /health
```

### Deployment Steps

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Restructure to microservices architecture"
   git push
   ```

2. **Deploy on Render**:
   - Option A: Use Blueprint (render.yaml)
     - Go to Render Dashboard
     - New → Blueprint
     - Connect repository
     - Render will create both services automatically

   - Option B: Create services manually
     - Create "darkhorses-workers" web service (rootDir: workers)
     - Create "darkhorses-api" web service (rootDir: api)

3. **Set Environment Variables**:
   Both services need the same environment variables (see above)

4. **Verify Deployment**:
   - Workers: Check logs for "🏇 DarkHorses Background Workers" and scheduler status
   - API: Access health endpoint and dashboard UI

## Cost Comparison

### Old Monolithic Architecture
- 1 Render service (API + Workers in one process): **$7/month**

### New Microservices Architecture
- Workers service (Starter plan, always-on): **$7/month**
- API service (Starter plan, always-on): **$7/month**
- **Total: $14/month**

**Trade-off**:
- Cost increase: +$7/month
- Benefits:
  - Independent scaling
  - Independent deployment (can update API without affecting data collection)
  - Clearer separation of concerns
  - Easier debugging (isolated logs)

## Testing Locally

### Test Workers

```bash
cd workers
python3 start_workers.py
```

Expected output:
```
🏇 DarkHorses Background Workers
Starting data collection services:
  1. Live Odds Scheduler (adaptive intervals)
  2. Historical Odds Scheduler (daily at 1:00 AM)
  3. Statistics Updater (every 10 minutes)

⚠️  No HTTP server - workers only write to database
```

### Test API

```bash
cd api
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then visit:
- Dashboard: http://localhost:8000/
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Migration from Monolithic

**What Changed**:

1. **Code Organization**:
   - Workers code moved to `workers/` directory
   - API code moved to `api/` directory
   - Old `odds_api/` directory kept for reference (not deployed)

2. **Entry Points**:
   - Workers: `workers/start_workers.py` (no HTTP)
   - API: `api/main.py` via uvicorn (HTTP server)
   - Old: `odds_api/start.py` (ran both in one process)

3. **API Changes**:
   - Removed `POST /api/statistics/refresh` (now automatic via workers)
   - Removed `GET /api/scheduler-health` (thread checking not applicable)
   - Updated `GET /api/scheduler-status` to read from workers' JSON file

4. **Dependencies**:
   - Split into two `requirements.txt` files
   - Workers: No FastAPI/uvicorn
   - API: No schedule library

5. **Deployment**:
   - Was: 1 Render service
   - Now: 2 Render services

**What Stayed the Same**:

- Database schema (no changes)
- Data collection logic (live_odds, historical_odds, odds_statistics)
- API endpoints (read operations)
- Dashboard UI
- Environment variables
- Scheduler timing and logic

## Rollback Plan

If issues arise, can quickly rollback to monolithic:

1. Rename `_legacy_monolithic/` back to `odds_api/`
2. Update `render.yaml` to use `odds_api/` with `start.py` entry point
3. Push changes and deploy
4. Suspend new microservices on Render

The old monolithic code is preserved in `_legacy_monolithic/` directory.

See `_legacy_monolithic/README_LEGACY.md` for detailed rollback instructions.

## Future Enhancements

- Add Redis for caching between services
- Implement webhooks from workers to API for real-time updates
- Add monitoring and alerting (Sentry, DataDog)
- Consider using Render's background worker type instead of web service for workers
- Add rate limiting to API endpoints
- Implement API authentication
