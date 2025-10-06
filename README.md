# DarkHorses Backend Workers

Background data collection workers for horse racing odds from The Racing API.

## 🏗️ Repository Structure

This repository contains **3 independent worker services** for data collection:

### Worker Services

```
DarkHorses-Backend-Workers/
├── live-odds-worker/          # Service 1: Live odds collection
│   ├── cron_live.py           # Main scheduler
│   ├── requirements.txt
│   ├── render.yaml
│   └── README_WORKER.md
│
├── historical-odds-worker/    # Service 2: Historical backfill
│   ├── cron_historical.py     # Main scheduler
│   ├── requirements.txt
│   ├── render.yaml
│   └── README_WORKER.md
│
└── statistics-worker/         # Service 3: Statistics generation
    ├── update_stats.py        # Main script
    ├── requirements.txt
    ├── render.yaml
    └── README_WORKER.md
```

### Extracted APIs (For Deployment Elsewhere)

```
extracted-apis/
├── odds-api/                  # DarkHorses Odds API
│   ├── main.py               # FastAPI app
│   ├── static/index.html     # Dashboard UI
│   ├── requirements.txt
│   ├── render.yaml
│   └── README.md
│
└── masters-api/               # Racing Masters Reference Data API
    ├── main.py               # FastAPI app (from Racing-API-Masters)
    ├── requirements.txt
    ├── render.yaml
    └── README.md
```

## 📊 Services Overview

### 1. Live Odds Worker

**Purpose**: Collects real-time odds from The Racing API for current/upcoming races

**Features**:
- Adaptive scheduling (10s to 15min based on race proximity)
- 26 bookmakers tracked
- Stops updating when race starts
- Writes to: `ra_odds_live` table

**Deploy**: `cd live-odds-worker && render deploy`

**Cost**: $7/month (Render Starter plan)

---

### 2. Historical Odds Worker

**Purpose**: Backfills historical race results and final odds from 2015-present

**Features**:
- Daily at 1:00 AM UK time
- Historical data from 2015
- Smart resume (skips completed dates)
- Writes to: `ra_odds_historical` table

**Deploy**: `cd historical-odds-worker && render deploy`

**Cost**: $7/month (Render Starter plan)

---

### 3. Statistics Worker

**Purpose**: Generates analytics and statistics from collected odds data

**Features**:
- Runs every 10 minutes
- Exports to JSON files
- Direct PostgreSQL for complex queries
- Writes to: `output/*.json` files

**Deploy**: `cd statistics-worker && render deploy`

**Cost**: $7/month (Render Starter plan)

---

### Total Worker Cost: $21/month (3 × $7)

## 🔌 Extracted APIs (Deploy Separately)

### Odds API

FastAPI service with:
- Live odds endpoints
- Historical odds endpoints
- Statistics viewer
- Kanban dashboard UI

**Cost**: $7/month or Free tier

### Masters API

FastAPI service with:
- Courses, bookmakers, jockeys, trainers, owners
- Horses with pedigree
- Races and results
- 18 REST endpoints

**Cost**: $7/month or Free tier

---

## 🚀 Quick Start

### Deploy All Workers to Render.com

Each worker is independently deployable:

```bash
# Deploy live odds worker
cd live-odds-worker
# Push to GitHub, then deploy via Render dashboard using render.yaml

# Deploy historical odds worker
cd historical-odds-worker
# Push to GitHub, then deploy via Render dashboard using render.yaml

# Deploy statistics worker
cd statistics-worker
# Push to GitHub, then deploy via Render dashboard using render.yaml
```

### Environment Variables

Each worker needs specific environment variables (see `.env.example` in each directory):

**Live & Historical Workers**:
```bash
RACING_API_USERNAME=your_username
RACING_API_PASSWORD=your_password
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key
```

**Statistics Worker**:
```bash
DATABASE_URL=postgresql://postgres:password@db.supabase.co:5432/postgres
```

## 🗄️ Database

All workers write to Supabase PostgreSQL:

**Tables**:
- `ra_odds_live` (31 columns) - Current race odds
- `ra_odds_historical` - Historical race data
- `ra_odds_statistics` - Analytics data

**Setup**: Run SQL scripts in `sql/` directory

## 📝 Local Development

Each worker can run independently:

```bash
# Live odds worker
cd live-odds-worker
pip install -r requirements.txt
python3 cron_live.py

# Historical odds worker
cd historical-odds-worker
pip install -r requirements.txt
python3 cron_historical.py

# Statistics worker
cd statistics-worker
pip install -r requirements.txt
python3 update_stats.py --loop
```

## 🏛️ Architecture

### Workers-Only Repository

This repository contains **ONLY background workers** - NO API code is deployed from here.

APIs are extracted to `extracted-apis/` folder for deployment in a separate API repository.

### Data Flow

```
Racing API
    ↓
Live Odds Worker → Supabase (ra_odds_live)
    ↓
Historical Worker → Supabase (ra_odds_historical)
    ↓
Statistics Worker → JSON files (output/)
    ↓
Odds API (separate deployment) → Reads from Supabase
Masters API (separate deployment) → Reads from Supabase
```

## 📂 Legacy Code

Old consolidated code is archived in `_legacy_monolithic/` and `workers/` directories.

These are kept for reference but not used in production.

## 🔍 Monitoring

Check worker logs:
- **Local**: Each worker has `logs/` directory
- **Render**: Dashboard → Service → Logs tab

Verify data collection:
```sql
-- Check live odds
SELECT COUNT(*), MAX(fetched_at)
FROM ra_odds_live
WHERE race_date >= CURRENT_DATE;

-- Check historical coverage
SELECT MIN(race_date), MAX(race_date), COUNT(DISTINCT race_date)
FROM ra_odds_historical;
```

## 📚 Documentation

- **Live Odds Worker**: See `live-odds-worker/README_WORKER.md`
- **Historical Worker**: See `historical-odds-worker/README_WORKER.md`
- **Statistics Worker**: See `statistics-worker/README_WORKER.md`
- **Odds API**: See `extracted-apis/odds-api/README.md`
- **Masters API**: See `extracted-apis/masters-api/README.md`
- **Technical Details**: See `CLAUDE.md` for detailed implementation notes

## 🆘 Troubleshooting

### Workers Not Collecting Data
- Verify Racing API credentials
- Check Supabase connection
- Review worker logs on Render

### Service Spins Down
- **Must use Starter plan** ($7/month) - free tier spins down after 15 minutes
- Workers need always-on to run schedulers

### Database Connection Issues
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` for workers
- Verify `DATABASE_URL` for statistics worker
- Check Supabase database is accessible

## 💰 Cost Summary

**Workers (this repo)**:
- Live Odds Worker: $7/month
- Historical Worker: $7/month
- Statistics Worker: $7/month
- **Subtotal**: $21/month

**APIs (deployed separately)**:
- Odds API: $7/month or Free
- Masters API: $7/month or Free
- **Subtotal**: $0-14/month

**Total System**: $21-35/month

## 📄 License

See LICENSE file for details.
