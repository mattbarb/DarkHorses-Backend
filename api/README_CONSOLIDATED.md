# DarkHorses Racing Odds - All-in-One System

Complete racing odds system with API, dashboard UI, and automated schedulers - all running in a single process.

## 🎯 What's Included

This consolidated system includes:

1. **📊 Dashboard UI** - Beautiful web interface at `/`
2. **🔌 REST API** - Full API with live/historical odds at `/api/*`
3. **⏰ Live Odds Scheduler** - Fetches odds every 5 minutes
4. **📚 Historical Odds Scheduler** - Daily fetch at 1:00 AM UK time
5. **📈 Statistics Tracker** - Auto-updates every 10 minutes

All services run together in **one process** - perfect for deployment!

## 🚀 Quick Start

### Local Development

```bash
cd api

# Install dependencies
pip install -r requirements.txt

# Set environment variables (create .env file)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key_here
DATABASE_URL=postgresql://postgres:password@host:5432/postgres

# Run everything
python3 start.py
```

Visit:
- **Dashboard UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📁 File Structure

```
api/
├── start.py                    # Main entry point - starts everything
├── main.py                     # FastAPI application
├── scheduler.py                # Consolidated background scheduler
├── requirements.txt            # Python dependencies
├── static/
│   └── index.html             # Dashboard UI
├── logs/                       # Application logs
├── render.yaml                # Render.com deployment config
└── README.md                  # This file
```

## 🎨 Dashboard Features

The web UI shows:

- **📅 Scheduler Status** - Active schedules and timing
- **🔴 Live Odds** - Current odds and upcoming races
- **📚 Historical Data** - Archive coverage and stats
- **📊 System Statistics** - Real-time metrics
- **📋 Recent Activity** - Latest odds updates

Auto-refreshes every 30 seconds!

## 🔌 API Endpoints

### Core Endpoints

```bash
GET /                          # Dashboard UI
GET /health                    # Health check
GET /docs                      # API documentation (Swagger)
GET /redoc                     # Alternative API docs
```

### Data Endpoints

```bash
GET /api/live-odds             # Live odds with filtering
GET /api/live-odds/upcoming-races  # Upcoming races
GET /api/historical-odds       # Historical odds
GET /api/statistics            # System statistics
GET /api/scheduler-status      # Scheduler information
GET /api/bookmakers            # List of bookmakers
GET /api/courses               # List of courses
```

See full API documentation at `/docs` when running.

## ⏰ Scheduler Configuration

### Live Odds Scheduler
- **Frequency**: Every 5 minutes
- **Coverage**: Today + Tomorrow (GB & IRE)
- **Adaptive**: Increases to 1 min when race starting soon
- **Stops**: When race starts

### Historical Odds Scheduler
- **Frequency**: Daily at 1:00 AM UK time
- **Coverage**: Yesterday's final odds and results
- **Backfill**: On-demand for 2015-present

### Statistics Updater
- **Frequency**: Every 10 minutes
- **Trigger**: Also runs after each fetch cycle
- **Output**: JSON files in `odds_statistics/output/`

## 🌐 Deployment to Render.com

### Prerequisites
- GitHub repository
- Render.com account
- Supabase credentials

### Deploy Steps

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Add consolidated racing odds system"
   git push origin main
   ```

2. **Create Render service**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - New → Web Service
   - Connect your GitHub repo
   - Configure:
     - Root Directory: `api`
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `python3 start.py`
     - Plan: **Starter** ($7/month - required for always-on scheduler)

3. **Add environment variables**
   ```
   SUPABASE_URL=https://amsjvmlaknnvppxsgpfk.supabase.co
   SUPABASE_SERVICE_KEY=your_service_key_here
   DATABASE_URL=postgresql://postgres:password@db.amsjvmlaknnvppxsgpfk.supabase.co:5432/postgres
   ```

4. **Deploy!**
   - Click "Create Web Service"
   - Wait for deployment
   - Visit your URL: `https://darkhorses-racing-odds.onrender.com`

### Important: Plan Requirements

**⚠️ Must use Starter plan ($7/month) or higher**

The free tier spins down after 15 minutes of inactivity, which would stop the background scheduler. The Starter plan keeps everything running 24/7.

## 🔧 Configuration

### Environment Variables

Required:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key_here
DATABASE_URL=postgresql://user:pass@host:5432/db
```

Optional:
```bash
PORT=8000                      # API server port (Render sets this automatically)
HOST=0.0.0.0                   # API server host
```

### Customize Scheduler Timing

Edit `scheduler.py`:

```python
# Change live odds frequency
schedule.every(5).minutes.do(self.run_live_odds)  # Change to 10, 15, etc.

# Change historical odds time
schedule.every().day.at("01:00").do(self.run_historical_odds)  # Change time

# Change statistics frequency
schedule.every(10).minutes.do(self.run_statistics_update)
```

## 📊 Monitoring

### View Logs

**Render Dashboard:**
- Go to your service → Logs tab
- See real-time logs from all components

**Local:**
```bash
# Main application log
tail -f api/logs/scheduler.log

# Individual service logs
tail -f live_odds/logs/cron_live.log
tail -f historical_odds/logs/cron_historical.log
tail -f odds_statistics/logs/stats_tracker.log
```

### Health Monitoring

```bash
# Health check endpoint
curl https://your-app.onrender.com/health

# Scheduler status
curl https://your-app.onrender.com/api/scheduler-status
```

## 🐛 Troubleshooting

### Services won't start

**Check environment variables:**
```bash
# Make sure all required vars are set
python3 -c "import os; print(os.getenv('SUPABASE_URL'))"
```

### Scheduler not running

**Check logs:**
```bash
# Look for scheduler startup messages
grep "Consolidated scheduler started" api/logs/scheduler.log
```

**Verify on Render:**
- Must use Starter plan or higher (not free tier)
- Free tier spins down and stops scheduler

### Statistics not updating

**Check output directory:**
```bash
ls -la odds_statistics/output/
```

**Generate manually:**
```bash
cd odds_statistics
python3 update_stats.py --table all
```

### UI not loading

**Check static files:**
```bash
ls -la api/static/
# Should contain index.html
```

**Visit API docs instead:**
```
http://localhost:8000/docs
```

## 🔐 Security Notes

### Production Checklist

1. **Update CORS settings** in `main.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],  # Not "*"
       ...
   )
   ```

2. **Add rate limiting**:
   ```bash
   pip install slowapi
   ```

3. **Use environment variables** - Never commit credentials!

4. **Enable HTTPS** - Render provides this automatically

5. **Monitor logs** - Set up alerts for errors

## 💰 Cost Estimate

### Render.com Hosting
- **Starter Plan**: $7/month (required for scheduler)
- **Professional**: $25/month (more resources)

### Supabase Database
- **Free Tier**: 500MB database, 2GB bandwidth
- **Pro**: $25/month (8GB database, 50GB bandwidth)

**Total minimum**: $7/month (Render Starter + Supabase Free)

## 📈 Performance

### Expected Load
- **API requests**: ~100 req/min for typical use
- **Database queries**: ~50 queries/min (scheduler + API)
- **Memory usage**: ~200-400MB
- **CPU usage**: Low (~5-10%)

### Scaling
- Starter plan handles up to 1000 req/min
- For higher loads, upgrade to Professional plan
- Consider Redis caching for frequently accessed data

## 🎯 Next Steps

### After Deployment

1. ✅ Test all endpoints
2. ✅ Verify schedulers are running (check logs)
3. ✅ Monitor first 24 hours
4. ⚠️ Set up error notifications
5. ⚠️ Add custom domain (optional)
6. ⚠️ Implement rate limiting
7. ⚠️ Add authentication for admin features

### Future Enhancements

- [ ] WebSocket support for real-time odds
- [ ] Admin panel for managing schedulers
- [ ] Email alerts for errors
- [ ] Advanced analytics dashboard
- [ ] CSV/Excel export functionality
- [ ] Historical data comparison tools

## 📚 Additional Resources

- **API Documentation**: Available at `/docs` when running
- **Render Docs**: https://render.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Supabase Docs**: https://supabase.com/docs

## 🆘 Support

If you encounter issues:

1. Check logs first
2. Verify environment variables
3. Test API endpoints manually
4. Review scheduler status at `/api/scheduler-status`

## 🎉 Summary

You now have a complete, production-ready racing odds system with:

- ✅ Beautiful dashboard UI
- ✅ Full REST API
- ✅ Automated data collection (live + historical)
- ✅ Real-time statistics
- ✅ Easy deployment to Render.com
- ✅ All in one process!

**Start command:**
```bash
python3 start.py
```

**That's it!** 🏇
