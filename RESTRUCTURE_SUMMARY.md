# Repository Restructure Summary

**Date**: October 6, 2025
**Objective**: Separate workers and APIs into independent deployable services

## ✅ What Was Completed

### 1. Split Workers into 3 Independent Services

Created 3 separate worker directories, each ready for independent deployment:

#### Live Odds Worker
- **Location**: `live-odds-worker/`
- **Main File**: `cron_live.py`
- **Purpose**: Collects real-time odds with adaptive scheduling
- **Dependencies**: Racing API credentials + Supabase
- **Deployment**: Render.com Background Worker ($7/month)

#### Historical Odds Worker
- **Location**: `historical-odds-worker/`
- **Main File**: `cron_historical.py`
- **Purpose**: Daily backfill of historical race data
- **Dependencies**: Racing API credentials + Supabase
- **Deployment**: Render.com Background Worker ($7/month)

#### Statistics Worker
- **Location**: `statistics-worker/`
- **Main File**: `update_stats.py` (with new `--loop` flag)
- **Purpose**: Generates analytics every 10 minutes
- **Dependencies**: PostgreSQL direct connection
- **Deployment**: Render.com Background Worker ($7/month)

### 2. Extracted APIs to Separate Folder

Created `extracted-apis/` folder with 2 complete API services:

#### Odds API
- **Location**: `extracted-apis/odds-api/`
- **Source**: Extracted from `_legacy_monolithic/main.py`
- **Features**:
  - Live odds endpoints
  - Historical odds endpoints
  - Statistics viewer
  - Kanban dashboard UI (`static/index.html`)
- **Deployment**: Render.com Web Service ($7/month or Free)

#### Masters API
- **Location**: `extracted-apis/masters-api/`
- **Source**: Extracted from Racing-API-Masters (`api_service.py`)
- **Features**:
  - 18 REST endpoints
  - Courses, bookmakers, jockeys, trainers, owners
  - Horses with pedigree
  - Races and results
- **Deployment**: Render.com Web Service ($7/month or Free)

### 3. Complete Configuration for Each Service

Every service now has:
- ✅ `render.yaml` - Deployment configuration
- ✅ `requirements.txt` - Python dependencies
- ✅ `.env.example` - Environment variable template
- ✅ `README.md` or `README_WORKER.md` - Documentation

### 4. Updated Documentation

- ✅ `README.md` - Root documentation with new architecture
- ✅ `CLAUDE.md` - Technical implementation notes (updated earlier)
- ✅ Individual READMEs for each service

## 📊 Architecture Before vs After

### Before (Consolidated)
```
DarkHorses-Backend/
└── workers/
    ├── start_workers.py (runs all 3 schedulers)
    ├── scheduler.py
    ├── live_odds/
    ├── historical_odds/
    └── odds_statistics/

Cost: $7/month (1 service)
API: Mixed with workers
```

### After (Microservices)
```
DarkHorses-Backend-Workers/
├── live-odds-worker/          # Independent service
├── historical-odds-worker/    # Independent service
├── statistics-worker/         # Independent service
└── extracted-apis/
    ├── odds-api/              # Independent API
    └── masters-api/           # Independent API

Workers Cost: $21/month (3 services)
APIs Cost: $0-14/month (deployed separately)
Total: $21-35/month
```

## 🎯 Benefits of New Architecture

### 1. Independent Scaling
- Each worker can be scaled independently
- APIs can scale based on traffic without affecting workers

### 2. Independent Deployment
- Update one service without redeploying others
- Reduces deployment risk

### 3. Independent Monitoring
- Separate logs for each service
- Easier to debug issues
- Clear separation of concerns

### 4. Fault Isolation
- If one worker fails, others continue running
- No single point of failure

### 5. Cost Flexibility
- Can choose Free tier for APIs if low traffic
- Can scale up individual workers as needed

## 📁 Files Created/Modified

### New Directories Created (5)
1. `live-odds-worker/`
2. `historical-odds-worker/`
3. `statistics-worker/`
4. `extracted-apis/odds-api/`
5. `extracted-apis/masters-api/`

### New Configuration Files (15)
1. `live-odds-worker/render.yaml`
2. `live-odds-worker/.env.example`
3. `live-odds-worker/README_WORKER.md`
4. `historical-odds-worker/render.yaml`
5. `historical-odds-worker/.env.example`
6. `historical-odds-worker/README_WORKER.md`
7. `statistics-worker/render.yaml`
8. `statistics-worker/.env.example`
9. `statistics-worker/README_WORKER.md`
10. `extracted-apis/odds-api/render.yaml`
11. `extracted-apis/odds-api/requirements.txt`
12. `extracted-apis/odds-api/.env.example`
13. `extracted-apis/odds-api/README.md`
14. `extracted-apis/masters-api/render.yaml`
15. `extracted-apis/masters-api/.env.example`
16. `extracted-apis/masters-api/README.md`

### Modified Files (3)
1. `README.md` - Complete rewrite for new architecture
2. `CLAUDE.md` - Updated technical documentation
3. `statistics-worker/update_stats.py` - Added `--loop` flag

### Files Copied (44+ files)
- All files from `workers/live_odds/` → `live-odds-worker/`
- All files from `workers/historical_odds/` → `historical-odds-worker/`
- All files from `workers/odds_statistics/` → `statistics-worker/`
- `_legacy_monolithic/main.py` → `extracted-apis/odds-api/main.py`
- `_legacy_monolithic/static/index.html` → `extracted-apis/odds-api/static/index.html`
- Racing-API-Masters `api_service.py` → `extracted-apis/masters-api/main.py`

## 🚀 Next Steps

### For Deployment

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Restructure: Split into 3 workers + extract APIs"
   git push
   ```

2. **Deploy Each Worker on Render.com**
   - Create 3 new Background Worker services
   - Point each to respective directory
   - Use render.yaml from each directory
   - Set environment variables from .env.example

3. **Deploy APIs Separately**
   - Option A: Create new "Racing-APIs" repository
   - Copy `extracted-apis/` contents to new repo
   - Deploy both APIs from new repo
   - Option B: Deploy directly from `extracted-apis/` in this repo

### For Testing

Test each worker independently:
```bash
# Live odds
cd live-odds-worker
pip install -r requirements.txt
python3 cron_live.py

# Historical
cd historical-odds-worker
pip install -r requirements.txt
python3 cron_historical.py

# Statistics
cd statistics-worker
pip install -r requirements.txt
python3 update_stats.py --loop
```

Test APIs:
```bash
# Odds API
cd extracted-apis/odds-api
pip install -r requirements.txt
uvicorn main:app --port 8000

# Masters API
cd extracted-apis/masters-api
pip install -r requirements.txt
uvicorn main:app --port 8001
```

## 📝 Important Notes

### Legacy Code
- `workers/` directory contains old consolidated code
- `_legacy_monolithic/` contains archived code
- Both kept for reference but NOT used in production

### Database Requirements
All services use the same Supabase database with tables:
- `ra_odds_live`
- `ra_odds_historical`
- `ra_odds_statistics`

Run SQL scripts in `sql/` directory to create tables.

### Environment Variables
Each service needs different environment variables:
- Workers: Racing API credentials + Supabase
- Statistics: Direct PostgreSQL URL
- APIs: Supabase or PostgreSQL depending on needs

See `.env.example` in each directory for specifics.

## ✅ Success Criteria

All objectives met:
- ✅ 3 independent worker services created
- ✅ APIs extracted to separate folder
- ✅ Each service has complete configuration
- ✅ All documentation updated
- ✅ Ready for deployment

## 💰 Cost Analysis

### Current Consolidated (Pre-Restructure)
- 1 Worker service: $7/month
- **Total**: $7/month

### New Microservices (Post-Restructure)
- Live Odds Worker: $7/month
- Historical Worker: $7/month
- Statistics Worker: $7/month
- Odds API: $0-7/month
- Masters API: $0-7/month
- **Total**: $21-35/month

### Cost Increase
- Workers: +$14/month (3 instead of 1)
- APIs: +$0-14/month (extracted, deployed separately)
- **Total Increase**: +$14-28/month

### Value Proposition
- Independent scaling and deployment
- Better fault isolation
- Easier debugging and monitoring
- More flexible architecture for future growth

---

**Restructure Status**: ✅ COMPLETE

All code restructured and ready for deployment as independent microservices.
