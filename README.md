# DarkHorses Racing Odds Backend

Microservices architecture for collecting horse racing odds data from The Racing API.

## 🏗️ Architecture

This system uses a **microservices architecture** with two separate services:

### 1. **Workers Service** (`workers/`)
Background data collection service (no HTTP server):
- **Live Odds Scheduler**: Adaptive intervals (10s-15min based on race proximity)
- **Historical Odds Scheduler**: Daily at 1:00 AM UK time for completed races
- **Statistics Updater**: Every 10 minutes

**Writes to**: `ra_odds_live`, `ra_odds_historical`, `ra_odds_statistics` tables

### 2. **API Service** (`api/`)
Read-only HTTP API and dashboard UI:
- FastAPI server with Swagger docs
- Kanban-style race cards dashboard
- Query endpoints for live and historical odds
- Statistics viewer

**Reads from**: All database tables

---

📖 **For detailed architecture documentation, see [MICROSERVICES_ARCHITECTURE.md](MICROSERVICES_ARCHITECTURE.md)**

---

## Quick Start - Render.com Deployment

### Prerequisites

1. **Supabase Database Setup**
   ```bash
   # Run in Supabase SQL Editor:
   # 1. Tables from historical_odds/create_ra_odds_historical.sql
   # 2. Tables from live_odds/create_ra_odds_live.sql
   # 3. Service state table from create_service_state_table.sql
   ```

2. **Racing API Credentials**
   - Get credentials from The Racing API
   - Note your username and password

### Deploy to Render.com

#### Option 1: Using render.yaml (Recommended)

1. **Connect Repository to Render**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml`

2. **Set Environment Variables**

   In Render dashboard, set these **secret** variables for both services:

   ```bash
   RACING_API_USERNAME=<your_username>
   RACING_API_PASSWORD=<your_password>
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=<your_service_key>
   DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres
   ```

3. **Deploy**
   - Click "Apply" in Render dashboard
   - Both services will build and start automatically

#### Option 2: Manual Service Creation

1. **Historical Odds Service**
   ```
   Type: Background Worker
   Environment: Docker
   Dockerfile Path: ./historical_odds/Dockerfile
   Docker Context: ./historical_odds
   ```

2. **Live Odds Service**
   ```
   Type: Background Worker
   Environment: Docker
   Dockerfile Path: ./live_odds/Dockerfile
   Docker Context: ./live_odds
   ```

3. Add environment variables (same as above) to each service

## Environment Variables

See `.env.example` for all available variables.

### Required
- `RACING_API_USERNAME` - Racing API credentials
- `RACING_API_PASSWORD` - Racing API credentials
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service role key
- `DATABASE_URL` - PostgreSQL connection string

### Optional
- `LOG_LEVEL` - Logging level (default: INFO)
- `BACKFILL_START_YEAR` - Historical backfill start year (default: 2015)
- `PORT` - Live service port (default: 8080)

## Monitoring

### Check Logs
- Render Dashboard → Your Service → Logs tab
- Look for successful API calls and database inserts

### Database Queries

**Historical Service Progress:**
```sql
SELECT
    MIN(race_date) as earliest_date,
    MAX(race_date) as latest_date,
    COUNT(DISTINCT race_date) as dates_covered
FROM ra_odds_historical;
```

**Live Service Activity:**
```sql
SELECT
    race_date,
    COUNT(*) as odds_count,
    MAX(fetched_at) as last_fetch
FROM ra_odds_live
WHERE race_date >= CURRENT_DATE
GROUP BY race_date
ORDER BY race_date;
```

## Local Development

### Historical Service
```bash
cd historical_odds
pip install -r requirements.txt
cp .env.example .env  # Add your credentials
python3 cron_historical.py
```

### Live Service
```bash
cd live_odds
pip install -r requirements.txt
cp .env.example .env  # Add your credentials
python3 cron_live.py
```

## Architecture

```
DarkHorses-Backend/
├── render.yaml                    # Render.com configuration
├── .env.example                   # Environment variables template
├── create_service_state_table.sql # Database state management
│
├── historical_odds/               # Historical backfill service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── cron_historical.py        # Main scheduler
│   ├── historical_odds_fetcher.py
│   ├── historical_odds_client.py
│   └── create_ra_odds_historical.sql
│
└── live_odds/                     # Live odds service
    ├── Dockerfile
    ├── requirements.txt
    ├── cron_live.py              # Main scheduler
    ├── live_odds_fetcher.py
    ├── live_odds_client.py
    └── create_ra_odds_live.sql
```

## Troubleshooting

### No Data Being Collected
- Verify Racing API credentials are correct
- Check service logs for API errors
- Ensure Supabase connection string is valid
- Verify database tables exist

### Services Not Starting on Render
- Check Render build logs for errors
- Verify Docker context paths in render.yaml
- Ensure all required environment variables are set

### VPN Issues
**Note:** VPN configuration in `.env.local` is for local development only. Render.com containers cannot use VPN - ensure Racing API is accessible without VPN.

## Support

For service-specific documentation:
- [Historical Odds Service](./historical_odds/README.md)
- [Live Odds Service](./live_odds/README.md)

For issues:
- Check Render deployment logs
- Review Supabase connection status
- Verify Racing API access and limits
