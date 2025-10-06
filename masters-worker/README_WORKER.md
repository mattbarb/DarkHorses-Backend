# Masters Worker - Reference Data Collection

**Part of DarkHorses-Backend-Workers**

This worker fetches and maintains racing reference/master data from The Racing API.

## What It Does

Collects and synchronizes reference data including:
- **Courses** (racing venues - UK & Ireland only)
- **Bookmakers** (UK/Ireland bookmakers)
- **Jockeys** (filtered for UK/Ireland connections)
- **Trainers** (UK/Ireland trainers)
- **Owners** (filtered for UK/Ireland connections)
- **Horses** (filtered for UK/Ireland connections)
- **Race Cards** (upcoming races with runners)
- **Race Results** (historical results)

**Regional Filtering**: Automatically filters to include only UK (GB) and Ireland (IRE) racing.

## Deployment

### Architecture

This worker runs as a **SEPARATE Render.com service** from the main workers:

```
DarkHorses-Backend-Workers (Repository)
├── darkhorses-workers (Service 1)
│   ├── Live Odds Worker
│   ├── Historical Odds Worker
│   └── Statistics Worker
└── darkhorses-masters-worker (Service 2) ← THIS SERVICE
    └── Masters/Reference Data Worker
```

**Why Separate?**
- Different update schedules (daily/weekly/monthly vs. real-time)
- Independent scaling and monitoring
- Isolated failures don't affect live odds collection
- $7/month per service = $14/month total

### Render.com Deployment

Deployed via `render.yaml` in repository root:

```yaml
services:
  - type: web
    name: darkhorses-masters-worker
    rootDirectory: masters-worker
    startCommand: python3 render_worker.py
```

**Deployment Steps:**
1. Push to GitHub (auto-deploys if connected)
2. Or manually create service in Render dashboard
3. Select "DarkHorses-Backend-Workers" repository
4. Choose "darkhorses-masters-worker" service from render.yaml
5. Set environment variables (see below)

### Environment Variables (Render.com)

Required in Render dashboard:

```bash
RACING_API_USERNAME=<username>
RACING_API_PASSWORD=<password>
SUPABASE_URL=https://project.supabase.co
SUPABASE_SERVICE_KEY=<service_key>
DATABASE_URL=postgresql://postgres:pass@db.supabase.co:5432/postgres
LOG_LEVEL=INFO
```

## Update Schedule

The worker runs on this schedule:

| Entity | Frequency | Time | Rationale |
|--------|-----------|------|-----------|
| **Courses** | Monthly | 1st @ 3:00 AM | Rarely change |
| **Bookmakers** | Monthly | 1st @ 3:00 AM | Static list |
| **Jockeys** | Weekly | Sun @ 2:00 AM | New jockeys, updates |
| **Trainers** | Weekly | Sun @ 2:00 AM | New trainers, updates |
| **Owners** | Weekly | Sun @ 2:00 AM | New owners, updates |
| **Horses** | Weekly | Sun @ 2:00 AM | New horses, updates |
| **Race Cards** | Daily | 1:00 AM | New race cards daily |
| **Results** | Daily | 1:00 AM | Results daily |

**Implemented in**: `render_worker.py` using Python `schedule` library

## Database Tables

### Supabase Tables

- `racing_courses` - Racing venues
- `racing_bookmakers` - Bookmakers
- `racing_jockeys` - Jockey profiles
- `racing_trainers` - Trainer profiles
- `racing_owners` - Owner profiles
- `racing_horses` - Horse profiles
- `racing_races` - Race cards with runners
- `racing_results` - Historical results

**Note**: These tables are separate from the `ra_odds_*` tables used by the odds workers.

## Monitoring

### Health Checks

Run health check:
```bash
python health_check.py
```

Checks:
- Environment configuration
- Racing API connectivity
- Supabase connectivity
- Recent fetch success
- Error log analysis

### Data Quality

Run quality check:
```bash
python data_quality_check.py
```

Validates:
- Table row counts
- Data freshness
- Required fields
- Regional filtering (UK/Ireland)
- Data relationships

### Logs

Logs location on Render:
- View in Render dashboard under "Logs" tab
- Logs streamed in real-time
- Search and filter available

Local logs (when running locally):
```bash
tail -f logs/main.log
tail -f logs/health_check.log
```

## Local Development

### Setup

```bash
cd masters-worker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Manual Execution

```bash
# Fetch all entities (complete sync)
python main.py --all

# Daily update (races and results)
python main.py --daily

# Weekly update (people and horses)
python main.py --weekly

# Monthly update (courses and bookmakers)
python main.py --monthly

# Specific entities
python main.py --entities courses bookmakers
python main.py --entities races results

# Test mode (limited data)
python main.py --test --entities courses
```

### Run Worker Scheduler

```bash
# Run the scheduler (same as Render deployment)
python render_worker.py
```

This will run continuously with scheduled updates.

## Architecture Details

### File Structure

```
masters-worker/
├── config/              # Configuration
│   └── config.py
├── fetchers/            # Data fetchers
│   ├── courses_fetcher.py
│   ├── bookmakers_fetcher.py
│   ├── jockeys_fetcher.py
│   ├── trainers_fetcher.py
│   ├── owners_fetcher.py
│   ├── horses_fetcher.py
│   ├── races_fetcher.py
│   └── results_fetcher.py
├── utils/               # Utilities
│   ├── api_client.py
│   ├── supabase_client.py
│   ├── logger.py
│   └── regional_filter.py
├── main.py              # CLI orchestrator
├── render_worker.py     # Render.com worker
├── health_check.py      # Health monitoring
├── data_quality_check.py  # Quality validation
└── requirements.txt
```

### Key Components

1. **render_worker.py**: Continuous worker with scheduled tasks
2. **main.py**: Manual execution orchestrator
3. **fetchers/**: Individual entity fetchers
4. **utils/api_client.py**: Racing API client
5. **utils/supabase_client.py**: Database operations
6. **utils/regional_filter.py**: UK/Ireland filtering

## Troubleshooting

### Common Issues

**1. Worker Not Running**
- Check Render dashboard for deployment status
- Review deployment logs for errors
- Verify environment variables are set

**2. No Data Being Fetched**
- Check Racing API credentials
- Verify Supabase connection
- Check logs for API errors
- Run health check

**3. Authentication Errors**
```
Error: 401 Unauthorized
```
Solution: Verify `RACING_API_USERNAME` and `RACING_API_PASSWORD`

**4. Database Connection Failed**
```
Error: Could not connect to Supabase
```
Solution:
- Check `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
- Verify database is accessible
- Check service key permissions

**5. Missing Tables**
```
Error: relation "racing_courses" does not exist
```
Solution: Create database tables (see schema in original README.md)

### Debug Mode

Enable debug logging:
```bash
# In Render dashboard
LOG_LEVEL=DEBUG
```

Check specific entity:
```bash
python main.py --test --entities courses
```

## Performance

### Expected Performance

- **Courses**: ~60 records, < 1 minute
- **Bookmakers**: ~10 records, < 1 minute
- **Jockeys**: ~500-1000 records, 2-5 minutes
- **Trainers**: ~300-500 records, 2-3 minutes
- **Owners**: ~500-1000 records, 2-5 minutes
- **Horses**: ~5000-10000 records, 10-30 minutes
- **Races**: ~50-100 races/day, 5-10 minutes
- **Results**: ~100-200 results/day, 5-10 minutes

### Resource Usage

- **Memory**: ~200-300 MB
- **CPU**: Low (mostly I/O bound)
- **Network**: Moderate during fetch cycles
- **Storage**: Minimal (logs only)

## Cost

- **Render Starter Plan**: $7/month
- **Separate from odds workers**: $7/month additional
- **Total for all workers**: $14/month (2 services)

## Maintenance

### Regular Tasks

1. **Monitor logs** (weekly)
   - Check Render dashboard logs
   - Review fetch success rates

2. **Run health checks** (weekly)
   ```bash
   python health_check.py
   ```

3. **Validate data quality** (weekly)
   ```bash
   python data_quality_check.py
   ```

4. **Review database growth** (monthly)
   - Check table sizes in Supabase dashboard
   - Verify data completeness

## Integration with Other Workers

This worker is **independent** from the other workers but shares:
- Same Supabase database
- Same Racing API credentials
- Same environment variables

**Data Flow:**
```
Racing API
    ↓
Masters Worker → Supabase (racing_* tables)
    ↓
Other systems can query reference data
```

The odds workers (`ra_odds_*` tables) may reference this master data for lookups.

## Support

For issues:
1. Check Render deployment logs
2. Run `health_check.py`
3. Run `data_quality_check.py`
4. Review troubleshooting section above
5. Check original README.md for detailed documentation

## Related Documentation

- Main workers: See repository root README.md
- Deployment: See CLAUDE.md in repository root
- Database schema: See SQL files in repository
- Racing API: https://theracingapi.com/docs
