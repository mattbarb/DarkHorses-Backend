# DarkHorses Backend Workers

Background data collection service for horse racing odds from The Racing API.

## 🏗️ Repository Structure

This repository contains **ONE consolidated worker service** with organized module folders:

```
DarkHorses-Backend-Workers/
├── start_workers.py           # Main entry point (runs all 3 schedulers)
├── scheduler.py               # Consolidated scheduler
├── requirements.txt           # Combined dependencies
├── render.yaml                # Single service deployment
├── .env.example               # Environment variables
│
├── live-odds-worker/          # Live odds module
│   ├── cron_live.py           # Live odds scheduler
│   ├── live_odds_fetcher.py   # API fetching logic
│   ├── live_odds_client.py    # Database operations
│   └── utils/                 # Utilities
│
├── historical-odds-worker/    # Historical odds module
│   ├── cron_historical.py     # Historical scheduler
│   ├── historical_odds_fetcher.py
│   ├── historical_odds_client.py
│   └── backfill_historical.py # Manual backfill script
│
├── statistics-worker/         # Statistics module
│   ├── update_stats.py        # Statistics updater
│   ├── database.py            # Direct PostgreSQL queries
│   ├── collectors/            # Data collectors
│   └── formatters/            # Output formatters
│
├── sql/                       # Database schemas
│   ├── create_ra_odds_live.sql
│   └── create_ra_odds_historical.sql
│
└── _deprecated/               # Old/archived code (reference only)
```

## 🎯 Architecture

**Single Consolidated Service** running 3 schedulers:
- **Live Odds**: Adaptive intervals (10s-15min based on race proximity)
- **Historical Odds**: Daily at 1:00 AM UK time
- **Statistics**: Every 10 minutes

**Cost**: $7/month (ONE Render.com Starter service)

**Why consolidated?**
- Lower cost ($7 vs $21/month for 3 services)
- Simpler deployment (one service to manage)
- Shared resources and logging
- Still organized with separate module folders

## 🚀 Quick Start

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Run all workers
python3 start_workers.py
```

This starts all 3 schedulers in one process:
- Live odds with adaptive scheduling
- Historical odds (daily at 1:00 AM)
- Statistics updates (every 10 minutes)

### Run Individual Modules (Testing)

```bash
# Live odds only
cd live-odds-worker
python3 cron_live.py

# Historical odds only
cd historical-odds-worker
python3 cron_historical.py

# Statistics only
cd statistics-worker
python3 update_stats.py --loop
```

## 📊 What Each Module Does

### 1. Live Odds Worker

**Purpose**: Collects real-time odds for current/upcoming races

**Features**:
- Adaptive scheduling (10s to 15min based on race proximity)
- 26 bookmakers tracked
- Stops updating when race starts
- Writes to: `ra_odds_live` table

**How it works**:
1. Fetches upcoming races from Racing API
2. Parses embedded odds from each runner
3. Upserts to Supabase (handles duplicates)
4. Adjusts next fetch interval based on race timing

### 2. Historical Odds Worker

**Purpose**: Backfills historical race results and final odds

**Features**:
- Daily run at 1:00 AM UK time
- Historical data from 2015 to present
- Smart resume (skips completed dates)
- Writes to: `ra_odds_historical` table

**How it works**:
1. Determines yesterday's date
2. Fetches completed races and results
3. Captures final odds and finishing positions
4. Stores for analysis

### 3. Statistics Worker

**Purpose**: Generates analytics from collected odds data

**Features**:
- Runs every 10 minutes
- Exports to JSON files
- Direct PostgreSQL for complex queries
- Writes to: `statistics-worker/output/*.json`

**How it works**:
1. Queries ra_odds_live and ra_odds_historical
2. Calculates aggregate statistics
3. Formats as JSON
4. Saves to output directory

## 🗄️ Database

All workers write to Supabase PostgreSQL:

**Tables**:
- `ra_odds_live` (31 columns) - Current race odds
- `ra_odds_historical` - Historical race data
- `ra_odds_statistics` - Analytics data

**Setup**: Run SQL scripts in `sql/` directory

## 🚢 Deploy to Render.com

### Using render.yaml (Recommended)

1. **Connect Repository to Render**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml`

2. **Set Environment Variables**
   - `RACING_API_USERNAME`
   - `RACING_API_PASSWORD`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `DATABASE_URL`

3. **Deploy**
   - Click "Apply"
   - Service will build and start automatically
   - **Important**: Must use Starter plan ($7/month) - free tier spins down

### Manual Deployment

```bash
# Service Configuration
Service Name: darkhorses-workers
Service Type: Web Service (for always-on)
Build Command: pip install -r requirements.txt
Start Command: python3 start_workers.py
Plan: Starter ($7/month)
```

## 📝 Environment Variables

Required:
```bash
RACING_API_USERNAME=<username>
RACING_API_PASSWORD=<password>
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=<service_key>
DATABASE_URL=postgresql://postgres:password@db.supabase.co:5432/postgres
```

Optional:
```bash
LOG_LEVEL=INFO
```

## 🔍 Monitoring

### Check Logs

**Local**:
```bash
tail -f logs/workers.log
```

**Render**:
- Dashboard → darkhorses-workers → Logs tab

### Verify Data Collection

```sql
-- Check live odds
SELECT COUNT(*), MAX(fetched_at)
FROM ra_odds_live
WHERE race_date >= CURRENT_DATE;

-- Check historical coverage
SELECT MIN(race_date), MAX(race_date), COUNT(DISTINCT race_date)
FROM ra_odds_historical;
```

### Check Status File

```bash
cat logs/scheduler_status.json
```

Shows last run times and status for each worker.

## 🏛️ Architecture

### Data Flow

```
Racing API
    ↓
Live Odds Worker → ra_odds_live (Supabase)
    ↓
Historical Worker → ra_odds_historical (Supabase)
    ↓
Statistics Worker → JSON files (output/)
    ↓
API (separate repo) → Reads from Supabase
```

### Worker Organization

The codebase is organized into **3 modules** for clarity:
- `live-odds-worker/` - Real-time odds collection
- `historical-odds-worker/` - Historical backfill
- `statistics-worker/` - Analytics generation

But all run in **ONE process** via `start_workers.py` for cost efficiency.

## 🆘 Troubleshooting

### Workers Not Collecting Data
- Verify Racing API credentials
- Check Supabase connection
- Review logs in `logs/workers.log`

### Service Spins Down
- **Must use Starter plan** ($7/month)
- Free tier spins down after 15 minutes

### Database Connection Issues
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
- Verify `DATABASE_URL` for statistics worker
- Check database is accessible

### Import Errors
- Ensure all dependencies in requirements.txt are installed
- Check Python path configuration in start_workers.py

## 📚 Related Repositories

- **API**: [DarkHorses-Backend-API](https://github.com/mattbarb/DarkHorses-Backend-API) - Unified API for accessing odds data
- **Masters**: [Racing-API-Masters](https://github.com/mattbarb/Racing-API-Masters) - Racing reference data collection

## 📂 Deprecated Code

Old code has been moved to `_deprecated/` directory:
- Old consolidated workers system
- Original monolithic application
- Extracted APIs (now in separate repo)

See `_deprecated/README.md` for details. This code is kept for reference only.

## 💰 Cost Summary

**This Service**: $7/month (Render Starter plan)

**Complete System** (Workers + API):
- Workers: $7/month (this repo)
- API: $7/month or Free ([DarkHorses-Backend-API](https://github.com/mattbarb/DarkHorses-Backend-API))
- **Total**: $7-14/month

## 📄 License

See LICENSE file for details.

---

**Version**: 2.0.0
**Architecture**: Consolidated single-service
**Deployment**: Render.com Web Service
**Python**: 3.10+
