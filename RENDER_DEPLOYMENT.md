# Render.com Deployment Instructions

## Odds Workers Deployment

### Step 1: Create New Web Service (If Not Already Deployed)

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Click **"Connect a repository"**
4. Find and select **"DarkHorses-Odds-Workers"**

### Step 2: Service Configuration

Render will auto-detect `render.yaml` and show:

```
Service Name: darkhorses-odds-workers
Environment: Python 3
Build Command: pip install --upgrade pip && pip install -r requirements.txt
Start Command: python3 start_workers.py
Plan: Starter ($7/month) ⚠️ IMPORTANT - NOT Free tier
```

Click **"Apply"**

### Step 3: Add Environment Variables

Go to **"Environment"** tab and add these 5 variables:

```bash
RACING_API_USERNAME=l2fC3sZFIZmvpiMt6DdUCpEv
RACING_API_PASSWORD=R0pMr1L58WH3hUkpVtPcwYnw
SUPABASE_URL=https://amsjvmlaknnvppxsgpfk.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFtc2p2bWxha25udnBweHNncGZrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDAxNjQxNSwiZXhwIjoyMDY1NTkyNDE1fQ.8JiQWlaTBH18o8PvElYC5aBAKGw8cfdMBe8KbXTAukI
LOG_LEVEL=INFO
```

**How to add:**
- Click **"Add Environment Variable"**
- Paste the **Key** (e.g., `RACING_API_USERNAME`)
- Paste the **Value** (e.g., `l2fC3sZFIZmvpiMt6DdUCpEv`)
- Repeat for all 5 variables
- Click **"Save Changes"**

**Note**: `DATABASE_URL` is NO LONGER required (removed after statistics worker refactoring)

### Step 4: Verify Deployment

Go to **"Logs"** tab and look for:

```
🚀 Starting DarkHorses Odds Workers
📍 Initializing 3 schedulers:
   - Live Odds Worker (adaptive: 10s-15min)
   - Historical Odds Worker (daily 1:00 AM)
   - Statistics Worker (every 10 min)
✅ All schedulers running
```

### Step 5: Test Locally (Optional)

```bash
cd /Users/matthewbarber/Documents/GitHub/DarkHorses-Odds-Workers/tests
python3 run_all_tests.py
```

This will verify data is being collected correctly.

---

## Worker Schedule

The service runs 3 workers on different schedules:

| Worker | Frequency | Table(s) | Description |
|--------|-----------|----------|-------------|
| **Live Odds** | Adaptive (10s-15min) | `ra_odds_live` | Real-time odds based on race proximity |
| **Historical Odds** | Daily @ 1:00 AM | `ra_odds_historical` | Historical backfill and race results |
| **Statistics** | Every 10 minutes | N/A | Generates analytics JSON files |

**Adaptive Scheduling (Live Odds)**:
- 10 seconds when race is imminent (<5 min)
- 60 seconds when race is soon (<30 min)
- 5 minutes when race upcoming (<2 hours)
- 15 minutes default check interval

---

## Database Tables

This worker populates these Supabase tables:

- `ra_odds_live` - Current/upcoming race odds (31 columns, fixed odds only)
- `ra_odds_historical` - Historical race results and final odds (2.4M+ records from 2015-present)

**Note**: Exchange odds columns were removed (Racing API doesn't provide exchange data)

---

## Recent Changes

### October 2025 - Statistics Worker Refactored
- **REMOVED**: `DATABASE_URL` requirement
- **ADDED**: Supabase SDK support for statistics
- **BENEFIT**: Works from any network (no IPv6 issues)

### Repository Reorganization
- **RENAMED**: `DarkHorses-Backend-Workers` → `DarkHorses-Odds-Workers`
- **REMOVED**: Masters worker (moved to separate repository)
- **SIMPLIFIED**: Single service for odds collection only

---

## Troubleshooting

### Service won't start
- Check **"Logs"** tab for errors
- Verify all 5 environment variables are set
- Ensure **Starter plan** is selected (not Free tier)

### No odds being collected
- Check Racing API credentials are correct
- Verify Supabase URL and service key
- Check Racing API status: https://theracingapi.com
- Review logs for API errors

### Tests failing locally
```bash
# Make sure you have .env.local file
cp .env.example .env.local
# Fill in your credentials
nano .env.local
```

---

## Cost

- **Plan**: Render Starter - $7/month
- **Why not Free?**: Free tier spins down after 15 min of inactivity, which would stop the schedulers

---

## Related Services

- **DarkHorses-Masters-Workers**: https://github.com/mattbarb/DarkHorses-Masters-Workers
  - Reference data collection (courses, jockeys, trainers, etc.)
  - Separate Render service ($7/month)
  - Total system cost: $14/month

---

## Performance

Expected performance:
- **Live Odds**: ~858 odds per 3 races (26 bookmakers × 33 horses average)
- **Historical Odds**: ~100 dates per daily backfill cycle
- **Statistics**: Updates every 10 minutes with fresh analytics
- **Memory**: ~200-300 MB
- **CPU**: Low (mostly I/O bound)

---

## Support

For issues:
1. Check Render deployment logs
2. Run local tests: `python3 tests/run_all_tests.py`
3. Review `CLAUDE.md` for detailed documentation
4. Check Racing API status: https://theracingapi.com
