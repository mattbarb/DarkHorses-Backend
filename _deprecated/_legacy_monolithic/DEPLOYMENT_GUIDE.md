# DarkHorses Racing Odds - ONE Service Deployment Guide

## Overview

This guide shows you how to deploy the **complete** DarkHorses Racing Odds system as **ONE Render.com web service** for just **$7/month**.

### What's Included in ONE Service

When you run `python3 start.py`, you get everything:

1. **FastAPI Server** - REST API + Dashboard UI
2. **Live Odds Scheduler** - Fetches odds every 5 minutes
3. **Historical Odds Scheduler** - Daily fetch at 1:00 AM UK time
4. **Statistics Updater** - Updates stats every 10 minutes

All running in a **single process** - no separate workers needed!

### Cost Comparison

| Architecture | Services | Monthly Cost |
|-------------|----------|--------------|
| ❌ Old (Microservices) | 3 separate workers | $21/month |
| ✅ New (Consolidated) | 1 web service | $7/month |

**You save $14/month** by using the consolidated architecture!

---

## Prerequisites

Before you begin, ensure you have:

- [x] GitHub account with your code pushed
- [x] Render.com account (sign up at [render.com](https://render.com))
- [x] Supabase project with credentials
- [x] Racing API credentials (username & password)

---

## Step-by-Step Deployment

### Step 1: Prepare Your Repository

1. **Ensure your code is up to date:**
   ```bash
   cd /path/to/DarkHorses-Backend
   git pull origin main
   ```

2. **Verify the consolidated setup exists:**
   ```bash
   # Check that these files exist:
   ls -la api/start.py
   ls -la api/scheduler.py
   ls -la api/main.py
   ls -la api/render.yaml
   ```

3. **Push to GitHub if needed:**
   ```bash
   git add .
   git commit -m "Ready for consolidated deployment"
   git push origin main
   ```

### Step 2: Create Render Web Service

1. **Go to Render Dashboard:**
   - Visit [dashboard.render.com](https://dashboard.render.com)
   - Click **"New +"** → **"Web Service"**

2. **Connect Your Repository:**
   - Click **"Connect a repository"**
   - Authorize Render to access your GitHub
   - Select: `DarkHorses-Backend`

3. **Configure the Service:**

   **Basic Settings:**
   - **Name:** `darkhorses-racing-odds` (or your preferred name)
   - **Region:** Choose closest to UK (e.g., Frankfurt)
   - **Branch:** `main` (or your default branch)
   - **Root Directory:** `api` ⚠️ **IMPORTANT!**

   **Build & Deploy:**
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python3 start.py` ⚠️ **CRITICAL!**

   **Plan Selection:**
   - **Plan:** `Starter` ($7/month)
   - ⚠️ **Do NOT use Free tier** - it spins down and stops schedulers

### Step 3: Add Environment Variables

In Render Dashboard → Your Service → Environment, add these variables:

**Required Variables:**
```bash
RACING_API_USERNAME=your_username_here
RACING_API_PASSWORD=your_password_here
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres:password@db.yourproject.supabase.co:5432/postgres
```

**How to Get These Values:**

1. **Racing API Credentials:**
   - Login at [racingapi.com](https://racingapi.com)
   - Find your username and password in account settings

2. **Supabase URL:**
   - Go to your Supabase project
   - Settings → API → Project URL

3. **Supabase Service Key:**
   - Same location → API → service_role key (not anon key!)

4. **Database URL:**
   - Settings → Database → Connection string (URI)
   - Choose "Session pooler" or "Direct connection"
   - Format: `postgresql://postgres.[project-ref]:[password]@[host]:5432/postgres`

**Optional Variables:**
```bash
PORT=8000                    # Auto-set by Render, no need to add
LOG_LEVEL=INFO              # Optional: DEBUG for more verbose logs
```

### Step 4: Deploy!

1. **Click "Create Web Service"**
2. **Wait for deployment** (usually 2-3 minutes)
3. **Check the logs** for successful startup messages:
   ```
   🏇 DarkHorses Racing Odds System
   Starting all services:
     1. Background Scheduler (live odds, historical odds, statistics)
     2. FastAPI Server (API + Dashboard UI)
   🚀 Starting background scheduler...
   🚀 Starting API server...
   ```

4. **Your service is live!** Access it at:
   - **Dashboard:** `https://darkhorses-racing-odds.onrender.com`
   - **API Docs:** `https://darkhorses-racing-odds.onrender.com/docs`

---

## Verification Steps

### 1. Check Service Health

```bash
# Health check
curl https://your-service.onrender.com/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-10-04T12:00:00"
}
```

### 2. Verify Schedulers Are Running

```bash
# Check scheduler status
curl https://your-service.onrender.com/api/scheduler-status

# Should show all three schedulers configured
```

### 3. Test Data Endpoints

```bash
# Get live odds
curl https://your-service.onrender.com/api/live-odds?limit=5

# Get statistics
curl https://your-service.onrender.com/api/statistics
```

### 4. Monitor Logs

In Render Dashboard → Your Service → Logs:

**Look for these messages:**
```
✅ Consolidated scheduler started successfully
📋 Active schedules:
   - Live odds: Every 5 minutes
   - Historical odds: Daily at 1:00 AM UK time
   - Statistics: Every 10 minutes
🚀 Running initial fetch on startup...
```

---

## Understanding the Architecture

### How ONE Process Runs Everything

The `start.py` file uses Python threading:

1. **Main Thread** → Runs FastAPI server (API + UI)
2. **Background Thread** → Runs consolidated scheduler

Both threads run in the **same process** on Render.

### Scheduler Timing

| Scheduler | Frequency | Purpose |
|-----------|-----------|---------|
| Live Odds | Every 5 minutes | Fetch current odds for today/tomorrow's races |
| Historical Odds | Daily at 1:00 AM | Fetch yesterday's final odds and results |
| Statistics | Every 10 minutes | Update JSON stats files |

### Data Flow

```
Racing API → Live/Historical Fetchers → Supabase Database → Statistics Tracker → API/Dashboard
```

All managed by the ONE service!

---

## Troubleshooting

### Issue: Service Won't Start

**Symptom:** Deployment fails or crashes immediately

**Solutions:**
1. Check all environment variables are set correctly
2. Verify Root Directory is set to `api`
3. Ensure Start Command is `python3 start.py` (not `uvicorn main:app`)
4. Check logs for specific error messages

### Issue: Schedulers Not Running

**Symptom:** No data being collected, logs show only API startup

**Cause:** Using wrong start command or free tier

**Solutions:**
1. Verify Start Command: `python3 start.py` (NOT `uvicorn main:app`)
2. Upgrade to Starter plan - free tier spins down
3. Check logs for "Consolidated scheduler started successfully"

### Issue: Missing Racing API Credentials

**Symptom:** Errors like "Authentication failed" in logs

**Solutions:**
1. Verify `RACING_API_USERNAME` and `RACING_API_PASSWORD` are set
2. Check credentials work by logging into racingapi.com
3. Re-add environment variables in Render dashboard

### Issue: Database Connection Errors

**Symptom:** "Could not connect to database" or "Connection refused"

**Solutions:**
1. Verify `SUPABASE_URL` format: `https://project.supabase.co`
2. Verify `SUPABASE_SERVICE_KEY` is the service_role key (not anon key)
3. Check `DATABASE_URL` has correct password and hostname
4. Test database connection from Supabase dashboard

### Issue: Statistics Not Updating

**Symptom:** `/api/statistics` returns 404 or old data

**Solutions:**
1. Ensure `DATABASE_URL` is set (required for stats)
2. Check logs for "Statistics updated successfully" messages
3. Verify statistics directory exists: `odds_statistics/output/`
4. Wait 10 minutes for first stats update

### Issue: Cold Starts on Free Tier

**Symptom:** Service takes 30+ seconds to respond after inactivity

**Cause:** Free tier spins down after 15 minutes

**Solution:** Upgrade to Starter plan ($7/month) for 24/7 uptime

---

## Configuration Options

### Customizing Scheduler Timing

Edit `api/scheduler.py` to adjust frequencies:

```python
# Live odds - change from 5 to 10 minutes
schedule.every(10).minutes.do(self.run_live_odds)

# Historical odds - change time
schedule.every().day.at("02:00").do(self.run_historical_odds)

# Statistics - change from 10 to 15 minutes
schedule.every(15).minutes.do(self.run_statistics_update)
```

Redeploy after changes:
```bash
git add api/scheduler.py
git commit -m "Adjust scheduler timing"
git push origin main
```

Render will auto-deploy the changes!

### CORS Configuration

For production, restrict CORS to your frontend domain.

Edit `api/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.vercel.app",
        "https://darkhorses.com"
    ],  # NOT "*" in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Custom Domain (Optional)

1. Go to Render Dashboard → Your Service → Settings
2. Scroll to "Custom Domains"
3. Click "Add Custom Domain"
4. Enter your domain: `api.darkhorses.com`
5. Add DNS records as shown by Render
6. Wait for SSL certificate (automatic, ~5 minutes)

---

## Monitoring & Maintenance

### Health Monitoring

Set up external monitoring to check service health:

**UptimeRobot (Free):**
1. Sign up at [uptimerobot.com](https://uptimerobot.com)
2. Add monitor:
   - Type: HTTP(s)
   - URL: `https://your-service.onrender.com/health`
   - Interval: 5 minutes
3. Get alerts via email/SMS if service goes down

### Log Monitoring

**View Logs in Render:**
- Dashboard → Your Service → Logs
- Filter by time range
- Search for errors: `ERROR`, `FAILED`, `❌`

**Important Log Messages to Watch:**
```
✅ = Success
❌ = Error
⚠️ = Warning
🚀 = Starting
```

### Performance Metrics

**In Render Dashboard:**
- CPU Usage: Should be <30% normally
- Memory: Should be <500MB (1GB limit on Starter)
- Response Time: Should be <500ms for API calls

**If usage is high:**
1. Check for runaway processes in logs
2. Verify database queries are efficient
3. Consider upgrading to Professional plan ($25/month)

---

## Cost Breakdown

### Render.com Costs

| Plan | Price | Features |
|------|-------|----------|
| Free | $0 | Spins down after 15 min (NOT suitable) |
| Starter | $7/month | Always on, 512MB RAM (RECOMMENDED) |
| Professional | $25/month | 2GB RAM, autoscaling |

### Supabase Costs (Separate)

| Plan | Price | Limits |
|------|-------|--------|
| Free | $0 | 500MB database, 2GB bandwidth |
| Pro | $25/month | 8GB database, 50GB bandwidth |

### Total Minimum Cost

**Recommended Setup:**
- Render Starter: $7/month
- Supabase Free: $0/month
- **Total: $7/month**

This gives you a production-ready system with:
- 24/7 uptime
- All schedulers running
- API + Dashboard
- 500MB database

---

## Advanced Topics

### Scaling Considerations

**When to scale:**
- CPU usage consistently >70%
- Memory usage consistently >80%
- Response times >1 second

**Scaling options:**
1. Upgrade to Professional plan (vertical scaling)
2. Add Redis caching for frequently accessed data
3. Implement database connection pooling
4. Add CDN for static assets

### Security Best Practices

**Production Checklist:**
- [x] Use environment variables for all secrets
- [x] Restrict CORS to specific domains
- [x] Use HTTPS only (automatic on Render)
- [ ] Add rate limiting (recommended)
- [ ] Implement API key authentication for admin endpoints
- [ ] Enable Render's DDoS protection
- [ ] Set up log alerts for suspicious activity

### Backup & Recovery

**Database Backups:**
- Supabase automatically backs up daily
- Download manual backup: Supabase Dashboard → Database → Backups

**Code Backups:**
- GitHub is your backup
- Tag releases: `git tag v1.0.0 && git push --tags`

**Recovery Steps:**
1. Restore database from Supabase backup
2. Redeploy from GitHub tag
3. Verify services start correctly
4. Check data integrity

---

## Deployment Checklist

Use this checklist for your first deployment:

### Pre-Deployment
- [ ] Code pushed to GitHub
- [ ] All environment variables ready
- [ ] Supabase project configured
- [ ] Racing API credentials valid

### Deployment
- [ ] Created Render web service
- [ ] Set Root Directory to `api`
- [ ] Set Start Command to `python3 start.py`
- [ ] Selected Starter plan ($7/month)
- [ ] Added all environment variables
- [ ] Clicked "Create Web Service"

### Post-Deployment
- [ ] Service deployed successfully
- [ ] Health check returns 200 OK
- [ ] Schedulers running (check logs)
- [ ] API endpoints returning data
- [ ] Dashboard UI accessible
- [ ] Logs show no errors

### Production Readiness
- [ ] CORS configured for production
- [ ] Set up uptime monitoring
- [ ] Configured log alerts
- [ ] Custom domain added (optional)
- [ ] Rate limiting implemented (recommended)
- [ ] Documentation updated

---

## Getting Help

### Documentation Resources
- **API Docs:** `https://your-service.onrender.com/docs`
- **Render Docs:** [render.com/docs](https://render.com/docs)
- **FastAPI Docs:** [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **Supabase Docs:** [supabase.com/docs](https://supabase.com/docs)

### Common Commands

```bash
# View service status
curl https://your-service.onrender.com/health

# Check scheduler configuration
curl https://your-service.onrender.com/api/scheduler-status

# Test live odds endpoint
curl https://your-service.onrender.com/api/live-odds?limit=1

# Test statistics endpoint
curl https://your-service.onrender.com/api/statistics

# View API documentation
open https://your-service.onrender.com/docs
```

### Support Contacts
- **Render Support:** support@render.com
- **Supabase Support:** Via dashboard chat
- **Racing API Support:** Via racingapi.com support

---

## Summary

You now have a **complete, production-ready** racing odds system running on Render.com for just **$7/month**!

**What you deployed:**
- ✅ ONE web service (not three separate workers)
- ✅ FastAPI server with REST API
- ✅ Beautiful dashboard UI
- ✅ Live odds scheduler (every 5 min)
- ✅ Historical odds scheduler (daily 1 AM)
- ✅ Statistics tracker (every 10 min)

**All running 24/7 in a single process!**

**Next steps:**
1. Monitor your service for 24 hours
2. Verify data is being collected correctly
3. Set up uptime monitoring
4. Configure your production domain
5. Add any custom features you need

**Need to make changes?**
1. Update your code locally
2. Push to GitHub: `git push origin main`
3. Render auto-deploys in ~2 minutes
4. Check logs to verify deployment

---

**Congratulations on your deployment!** 🎉

Your racing odds system is now live and collecting data automatically.
