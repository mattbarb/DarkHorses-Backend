# Deploy to Render.com

## Prerequisites

- GitHub repository with your code
- Render.com account (free tier available)
- Supabase credentials (SUPABASE_URL and SUPABASE_SERVICE_KEY)

## Deployment Steps

### Option 1: One-Click Deploy (Blueprint)

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **"New +"** → **"Blueprint"**
4. Connect your GitHub repository
5. Render will detect `render.yaml` and configure automatically
6. Add environment variables (see below)
7. Click **"Apply"** to deploy

### Option 2: Manual Web Service Deploy

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:

   **Basic Settings:**
   - Name: `darkhorses-api`
   - Region: Choose closest to your users (e.g., Frankfurt for UK)
   - Branch: `main` (or your default branch)
   - Root Directory: `api`

   **Build & Deploy:**
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python3 start.py`

   **Plan:**
   - Free (for testing) or Starter ($7/month for production)

5. Add environment variables (see below)
6. Click **"Create Web Service"**

### Environment Variables

Add these in Render Dashboard → Your Service → Environment:

```
RACING_API_USERNAME=your_username
RACING_API_PASSWORD=your_password
SUPABASE_URL=https://amsjvmlaknnvppxsgpfk.supabase.co
SUPABASE_SERVICE_KEY=your_service_key_here
DATABASE_URL=postgresql://postgres:password@db.amsjvmlaknnvppxsgpfk.supabase.co:5432/postgres
```

**Important:** Don't commit these to GitHub! Add them only in Render's dashboard.

**Note:** DATABASE_URL is required for the statistics tracker to run direct PostgreSQL queries.

## Post-Deployment

### 1. Verify Deployment

Your API will be available at: `https://darkhorses-api.onrender.com`

Test endpoints:
```bash
# Health check
curl https://darkhorses-api.onrender.com/

# Scheduler status
curl https://darkhorses-api.onrender.com/api/scheduler-status

# Live odds
curl https://darkhorses-api.onrender.com/api/live-odds?limit=10
```

### 2. Access API Documentation

- Swagger UI: `https://darkhorses-api.onrender.com/docs`
- ReDoc: `https://darkhorses-api.onrender.com/redoc`

### 3. Configure CORS (if using with frontend)

Update `main.py` with your frontend domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.vercel.app",
        "https://darkhorses-api.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Render.com Features

### Free Tier Limitations
- ✅ 750 hours/month (enough for 24/7)
- ✅ Automatic HTTPS
- ✅ Auto-deploy on git push
- ⚠️ Spins down after 15 min inactivity (cold start ~30s)
- ⚠️ 512MB RAM limit

### Upgrading to Starter ($7/month)
- ✅ No spin down (always running)
- ✅ 1GB RAM
- ✅ Better performance
- ✅ Custom domains

## Monitoring

### Health Checks

Render automatically monitors: `https://darkhorses-api.onrender.com/`

If it returns 200 OK, service is healthy.

### Logs

View logs in Render Dashboard → Your Service → Logs

### Metrics

Free tier includes:
- CPU usage
- Memory usage
- Request count
- Response times

## Auto-Deploy on Git Push

Render automatically redeploys when you push to your configured branch:

```bash
git add .
git commit -m "Update API"
git push origin main
```

Render will:
1. Detect the push
2. Run build command
3. Deploy new version
4. Zero-downtime rollout

## Custom Domain (Optional)

1. Go to Settings → Custom Domains
2. Add your domain (e.g., `api.darkhorses.com`)
3. Configure DNS records as shown by Render
4. SSL certificate is automatic

## Troubleshooting

### Service Won't Start

**Check logs for errors:**
- Missing environment variables → Add in Render dashboard
- Import errors → Verify all dependencies in `requirements.txt`
- Port binding → Render sets `$PORT` automatically, don't hardcode

### Slow Cold Starts (Free Tier)

The free tier spins down after inactivity. Solutions:
- Upgrade to Starter plan ($7/month)
- Use a cron job to ping your API every 10 minutes
- Accept the 30-second cold start delay

### Statistics Not Loading

The API reads from `odds_statistics/output/` directory. On Render:
- These files are NOT included in deployment
- You need to generate them first

**Solution:** Run the statistics tracker locally and commit the JSON files:

```bash
# Generate stats locally
cd odds_statistics
python3 update_stats.py --table all

# Commit the output files
git add output/*.json
git commit -m "Add latest statistics"
git push
```

Or better: Set up a scheduled job to generate stats (see below).

## Production Recommendations

### 1. Use Starter Plan
Free tier has cold starts. For production, use Starter ($7/month).

### 2. Add Health Check Endpoint
Already included at `GET /` - returns 200 OK.

### 3. Environment-Specific Config

Add to `main.py`:
```python
import os

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

if ENVIRONMENT == 'production':
    # Production-specific settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://your-frontend.com"],
        ...
    )
```

Then in Render:
```
ENVIRONMENT=production
```

### 4. Rate Limiting

Add rate limiting for production:

```bash
pip install slowapi
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/live-odds")
@limiter.limit("100/minute")
def get_live_odds(...):
    ...
```

### 5. Caching

For better performance, add caching:

```bash
pip install fastapi-cache2[redis]
```

Or simple in-memory caching:

```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=100)
def get_cached_live_odds(cache_key: str):
    # Your query logic
    pass
```

## Cost Estimate

**Free Tier:**
- API: Free (with spin down)
- Total: $0/month

**Production Setup:**
- API (Starter): $7/month
- Total: $7/month

**Note:** Database (Supabase) is separate and has its own free tier.

## Next Steps

1. ✅ Deploy to Render
2. ✅ Test all endpoints
3. ⚠️ Set up scheduled statistics generation
4. ⚠️ Configure CORS for your frontend
5. ⚠️ Add rate limiting for production
6. ⚠️ Set up monitoring/alerts

## Background Schedulers (Included!)

**Important:** The consolidated system (`python3 start.py`) includes ALL background schedulers:
- Live odds scheduler (every 5 minutes)
- Historical odds scheduler (daily at 1:00 AM)
- Statistics updater (every 10 minutes)

These run automatically as background threads in the same process as the API. No separate cron jobs needed!

### Requirements for Background Tasks

**Must use Starter plan ($7/month) or higher:**
- Free tier spins down after 15 minutes of inactivity
- This would stop the background schedulers
- Starter plan keeps everything running 24/7

The `python3 start.py` command ensures all schedulers run continuously alongside the API server.
