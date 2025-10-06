# Racing API Reference Data Fetcher - Production

Production-ready system for fetching and maintaining UK and Ireland racing reference data from The Racing API into Supabase PostgreSQL database.

## Overview

This system automatically fetches and synchronizes racing reference data including:
- Racing courses (GB & IRE only)
- Bookmakers (UK/Ireland bookmakers)
- Jockeys (filtered for UK/Ireland connections)
- Trainers (UK/Ireland trainers)
- Owners (filtered for UK/Ireland connections)
- Horses (filtered for UK/Ireland connections)
- Race cards with runners (GB & IRE races)
- Race results (GB & IRE results)

**Regional Filtering**: All data is automatically filtered to include only UK (GB) and Ireland (IRE) racing.

## System Architecture

```
production/
├── config/              # Configuration management
│   └── config.py       # Environment and settings
├── fetchers/           # Data fetching modules
│   ├── courses_fetcher.py
│   ├── bookmakers_fetcher.py
│   ├── jockeys_fetcher.py
│   ├── trainers_fetcher.py
│   ├── owners_fetcher.py
│   ├── horses_fetcher.py
│   ├── races_fetcher.py
│   └── results_fetcher.py
├── utils/              # Utility modules
│   ├── api_client.py   # Racing API client
│   ├── supabase_client.py  # Supabase database client
│   ├── logger.py       # Logging utilities
│   └── regional_filter.py  # UK/Ireland filtering
├── logs/               # Log files
├── docker/             # Docker deployment (optional)
├── main.py             # Main orchestrator
├── health_check.py     # System health monitoring
├── data_quality_check.py  # Data validation
├── deploy.sh           # Deployment automation
├── crontab.txt         # Cron schedule
├── requirements.txt    # Python dependencies
└── .env.example        # Environment template
```

## Database Tables

### Core Tables
- `racing_courses` - Racing venues (UK & Ireland)
- `racing_bookmakers` - Bookmakers offering odds
- `racing_jockeys` - Jockey profiles
- `racing_trainers` - Trainer profiles
- `racing_owners` - Horse owner profiles
- `racing_horses` - Horse profiles

### Race Data Tables
- `racing_races` - Race cards with details and runners
- `racing_results` - Historical race results

## Prerequisites

### System Requirements
- Python 3.9 or higher
- Linux/Unix environment (macOS, Ubuntu, Debian, etc.)
- Virtual environment support
- Cron (for scheduling) or Docker (alternative)

### External Services
1. **The Racing API**
   - Sign up at: https://theracingapi.com
   - Get API credentials (username & password)
   - Subscription required for full data access

2. **Supabase PostgreSQL Database**
   - Create Supabase project: https://supabase.com
   - Get connection details (URL & service key)
   - Database tables must be created (see schema)

## Quick Start

### 1. Clone/Copy to Production Server

```bash
# Copy this entire production folder to your server
scp -r production/ user@server:/path/to/deployment/
```

### 2. Initial Setup

```bash
cd /path/to/deployment/production
./deploy.sh
```

The deployment script will:
- Check Python and dependencies
- Create virtual environment
- Install requirements
- Setup configuration
- Run test fetch
- Guide you through cron setup

### 3. Manual Setup (Alternative)

If you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your credentials
```

## Configuration

### Environment Variables

Edit `.env` with your credentials:

```bash
# Racing API
RACING_API_USERNAME=your_username
RACING_API_PASSWORD=your_password

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key

# Optional
RACING_API_TIMEOUT=30
LOG_LEVEL=INFO
```

### Regional Filtering

This system is configured for **UK and Ireland only**:
- Courses: Only GB and IRE region codes
- Races/Results: Only GB and IRE races
- People/Horses: Filtered post-fetch based on UK/Ireland connections

This is built into the system and requires no additional configuration.

## Usage

### Manual Execution

Activate virtual environment first:
```bash
source venv/bin/activate
```

**Fetch all entities** (complete sync):
```bash
python main.py --all
```

**Daily update** (races and results):
```bash
python main.py --daily
```

**Weekly update** (people and horses):
```bash
python main.py --weekly
```

**Monthly update** (courses and bookmakers):
```bash
python main.py --monthly
```

**Specific entities**:
```bash
python main.py --entities courses bookmakers
python main.py --entities races results
```

**Test mode** (limited data):
```bash
python main.py --test --entities courses
```

### Scheduled Execution (Cron)

#### Recommended Schedule

Edit `crontab.txt` with your paths, then install:

```bash
# Edit paths in crontab.txt
nano crontab.txt

# Install crontab
crontab crontab.txt

# Verify installation
crontab -l
```

#### Default Schedule

- **Daily** (1:00 AM): Fetch races and results
- **Weekly** (Sunday 2:00 AM): Fetch jockeys, trainers, owners, horses
- **Monthly** (1st day, 3:00 AM): Fetch courses and bookmakers
- **Hourly**: Health checks
- **Daily** (6:00 AM): Data quality checks

### Docker Deployment (Alternative)

Build and run with Docker:

```bash
cd docker/
docker-compose up -d
```

See `docker/README.md` for Docker-specific instructions.

## Monitoring

### Health Checks

Run system health check:
```bash
python health_check.py
```

Checks:
- Environment configuration
- Racing API connectivity
- Supabase connectivity
- Recent fetch success
- Error log analysis

Exit code: 0 = healthy, 1 = issues found

### Data Quality Checks

Run data quality validation:
```bash
python data_quality_check.py
```

Checks:
- Table row counts
- Data freshness
- Required fields
- Regional filtering
- Data relationships

Exit code: 0 = quality OK, 1 = quality issues

### Log Files

Logs are stored in `logs/` directory:

```bash
# Main application log
tail -f logs/main.log

# Cron job logs
tail -f logs/cron_daily.log
tail -f logs/cron_weekly.log
tail -f logs/cron_monthly.log

# Monitoring logs
tail -f logs/health_check.log
tail -f logs/data_quality_check.log

# Fetch results (JSON)
cat logs/fetch_results_YYYYMMDD_HHMMSS.json
```

## Data Update Frequency

### Recommended Schedule

| Entity | Update Frequency | Rationale |
|--------|-----------------|-----------|
| Courses | Monthly | Rarely change |
| Bookmakers | Monthly | Static list |
| Jockeys | Weekly | New jockeys, updates |
| Trainers | Weekly | New trainers, updates |
| Owners | Weekly | New owners, updates |
| Horses | Weekly | New horses, updates |
| Races | Daily | New race cards published daily |
| Results | Daily | Results published after races |

### High-Frequency Alternative

For near-real-time data, you can increase frequency:
- **Races/Results**: Every 6 hours or more frequently
- **People/Horses**: Daily
- **Courses/Bookmakers**: Weekly

Adjust in `crontab.txt` based on your needs and API rate limits.

## Troubleshooting

### Common Issues

#### 1. Authentication Failed
```
Error: 401 Unauthorized
```
**Solution**: Check `.env` credentials are correct

#### 2. Database Connection Failed
```
Error: Could not connect to Supabase
```
**Solution**:
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
- Check database is accessible from your server
- Verify service key has correct permissions

#### 3. No Data Fetched
```
Success: True, Fetched: 0, Inserted: 0
```
**Solution**:
- Check Racing API subscription is active
- Verify API credentials
- Check logs for API errors
- Verify regional filtering isn't too restrictive

#### 4. Cron Jobs Not Running
```
Expected logs not appearing
```
**Solution**:
- Verify crontab is installed: `crontab -l`
- Check cron service is running
- Verify paths in crontab.txt are absolute
- Check cron logs: `/var/log/syslog` or `journalctl -u cron`

#### 5. Import Errors
```
ModuleNotFoundError: No module named 'config'
```
**Solution**:
- Ensure you're using the virtual environment
- Run from the production directory
- Check `sys.path` includes current directory

### Debug Mode

Enable debug logging in `.env`:
```bash
LOG_LEVEL=DEBUG
```

Run with verbose output:
```bash
python -u main.py --test --entities courses 2>&1 | tee debug.log
```

### Check System Health

Quick health check:
```bash
# Check configuration
python -c "from config.config import get_config; get_config()"

# Test API connection
python -c "from utils.api_client import RacingAPIClient; RacingAPIClient().get('/courses', params={'limit_per_page': 1})"

# Test database connection
python -c "from utils.supabase_client import SupabaseClient; print(SupabaseClient().client.table('racing_courses').select('id').limit(1).execute())"
```

## Maintenance

### Regular Maintenance Tasks

1. **Monitor logs** (weekly)
   - Check for errors in log files
   - Review fetch success rates
   - Verify data quality

2. **Review data quality** (weekly)
   - Run `data_quality_check.py`
   - Check for data gaps
   - Verify regional filtering

3. **Update dependencies** (monthly)
   ```bash
   source venv/bin/activate
   pip list --outdated
   pip install --upgrade package_name
   ```

4. **Clean old logs** (monthly)
   ```bash
   # Keep last 30 days
   find logs/ -name "*.log" -mtime +30 -delete
   find logs/ -name "fetch_results_*.json" -mtime +30 -delete
   ```

5. **Backup configuration** (as needed)
   ```bash
   cp .env .env.backup
   ```

### Database Maintenance

1. **Check table sizes**
   ```sql
   SELECT
     schemaname,
     tablename,
     pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   WHERE tablename LIKE 'racing_%'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
   ```

2. **Vacuum and analyze** (monthly)
   ```sql
   VACUUM ANALYZE racing_courses;
   VACUUM ANALYZE racing_horses;
   -- etc for all tables
   ```

## Performance

### Expected Performance

- **Courses**: ~60 records, < 1 minute
- **Bookmakers**: ~10 records, < 1 minute
- **Jockeys**: ~500-1000 records, 2-5 minutes
- **Trainers**: ~300-500 records, 2-3 minutes
- **Owners**: ~500-1000 records, 2-5 minutes
- **Horses**: ~5000-10000 records, 10-30 minutes (with pagination)
- **Races**: ~50-100 races/day, 5-10 minutes
- **Results**: ~100-200 results/day, 5-10 minutes

### Optimization

1. **Batch size**: Adjust in `.env`
   ```bash
   SUPABASE_BATCH_SIZE=100  # Increase for faster inserts
   ```

2. **Pagination**: Limit horses fetch
   ```bash
   # In main.py, adjust horses config
   'horses': {'limit_per_page': 500, 'max_pages': 50}
   ```

3. **Parallel execution**: Run independent fetches in parallel
   ```bash
   python main.py --entities courses &
   python main.py --entities bookmakers &
   wait
   ```

## Security

### Best Practices

1. **Secure .env file**
   ```bash
   chmod 600 .env
   ```

2. **Use service account**: Create dedicated user for this system

3. **Limit database permissions**: Grant only required permissions

4. **Rotate credentials**: Update API and database credentials periodically

5. **Monitor access**: Review Supabase logs for unauthorized access

### Sensitive Files

Never commit these files to version control:
- `.env` - Contains credentials
- `logs/*.log` - May contain sensitive data
- `venv/` - Virtual environment

## Support

### Documentation
- The Racing API: https://theracingapi.com/docs
- Supabase: https://supabase.com/docs
- Python dotenv: https://pypi.org/project/python-dotenv/

### Contact
For issues with this system, review:
1. Log files in `logs/`
2. Troubleshooting section above
3. Run health and quality checks

## License

This system is for internal use with The Racing API and Supabase services.
Ensure you comply with:
- The Racing API Terms of Service
- Supabase Terms of Service
- Data protection regulations (GDPR, etc.)

## Version

Production Release v1.0
Generated: 2025-10-04
