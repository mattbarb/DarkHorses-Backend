# DarkHorses-Odds-Workers - Deployment Guide

## Overview

This guide covers deploying DarkHorses-Odds-Workers to production environments.

## Deployment Platforms

### Render (Recommended)

**Why Render:**
- Easy PostgreSQL setup
- Auto-deploys from GitHub
- Free tier available
- Built-in monitoring

**Steps:**

1. **Create Render Account:**
   - Go to https://render.com
   - Sign up with GitHub

2. **Create Web Service:**
   ```
   - New → Web Service
   - Connect repository: https://github.com/yourusername/DarkHorses-Odds-Workers
   - Branch: main
   - Build command: pip install -r requirements.txt
   - Start command: python main.py (or uvicorn main:app)
   ```

3. **Environment Variables:**
   ```
   DATABASE_URL=postgresql://...
   REDIS_URL=redis://...
   API_KEY=your_api_key
   LOG_LEVEL=INFO
   ```

4. **Add PostgreSQL:**
   ```
   - New → PostgreSQL
   - Link to web service
   - Copy DATABASE_URL to env vars
   ```

### Heroku (Alternative)

**Steps:**

1. **Install Heroku CLI:**
   ```bash
   brew install heroku/brew/heroku
   ```

2. **Create App:**
   ```bash
   heroku create DarkHorses-Odds-Workers
   ```

3. **Add PostgreSQL:**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

4. **Configure:**
   ```bash
   heroku config:set API_KEY=your_key
   heroku config:set LOG_LEVEL=INFO
   ```

5. **Deploy:**
   ```bash
   git push heroku main
   ```

### AWS (Enterprise)

See [AWS Deployment Guide](docs/AWS_DEPLOYMENT.md) for detailed AWS setup.

## Environment Configuration

### Required Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis (if needed)
REDIS_URL=redis://host:6379

# API Keys
API_KEY=your_api_key_here

# Application
LOG_LEVEL=INFO
WORKERS=4
```

### Optional Variables

```bash
# Feature flags
ENABLE_FEATURE_X=true

# Performance
MAX_CONNECTIONS=100
TIMEOUT=30

# Monitoring
SENTRY_DSN=https://...
```

## CI/CD Pipeline

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest

      - name: Deploy to Render
        run: |
          curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}
```

### Pre-deployment Checklist

- [ ] All tests passing
- [ ] Environment variables set
- [ ] Database migrations run
- [ ] Secrets configured
- [ ] Monitoring enabled
- [ ] Backups configured

## Database Migrations

### Running Migrations

```bash
# Render
render run python migrate.py

# Heroku
heroku run python migrate.py

# Local
python migrate.py
```

### Rollback

```bash
# Render
render run python migrate.py rollback

# Heroku
heroku run python migrate.py rollback
```

## Monitoring

### Logs

**Render:**
```bash
render logs
```

**Heroku:**
```bash
heroku logs --tail
```

### Metrics to Monitor

- Request count
- Response time (p50, p95, p99)
- Error rate
- Database connections
- Memory usage
- CPU usage

### Alerts

Set up alerts for:
- Error rate > 5%
- Response time > 2s
- Database connections > 80%
- Memory usage > 90%

## Scaling

### Horizontal Scaling

**Render:**
- Dashboard → Service → Scaling
- Increase instance count

**Heroku:**
```bash
heroku ps:scale web=3
```

### Vertical Scaling

**Render:**
- Upgrade instance type in dashboard

**Heroku:**
```bash
heroku ps:resize web=standard-2x
```

## Rollback Procedures

### Quick Rollback

**Render:**
- Dashboard → Service → Rollback to previous version

**Heroku:**
```bash
heroku rollback
```

### Full Rollback with Database

1. Stop new deployments
2. Rollback code
3. Rollback database migrations
4. Verify functionality
5. Monitor for issues

## Security

### Secrets Management

- Never commit secrets to git
- Use environment variables
- Rotate keys regularly
- Use secret management service (Vault, AWS Secrets Manager)

### SSL/TLS

- Render: Automatic SSL certificates
- Heroku: Automatic SSL
- AWS: Use ACM certificates

### Security Headers

Add to application:
```python
# FastAPI example
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response
```

## Backup Strategy

### Database Backups

**Automated:**
- Render: Daily automatic backups (retained 7 days)
- Heroku: Continuous protection ($50/mo)

**Manual:**
```bash
# Backup
pg_dump $DATABASE_URL > backup.sql

# Restore
psql $DATABASE_URL < backup.sql
```

### File Backups

If storing files:
- Use S3 or similar object storage
- Enable versioning
- Set lifecycle policies

## Troubleshooting

### Common Issues

**Issue 1: Deployment Fails**
- Check build logs
- Verify requirements.txt
- Check Python version

**Issue 2: App Crashes on Start**
- Check environment variables
- Verify database connection
- Check logs for errors

**Issue 3: Slow Performance**
- Scale horizontally
- Add caching layer
- Optimize database queries

## Cost Optimization

### Tips

1. **Use free tiers for development:**
   - Render: Free for basic services
   - Heroku: Free tier available

2. **Scale down when not needed:**
   - Reduce instances during off-hours
   - Use smaller instance types for non-prod

3. **Monitor usage:**
   - Set billing alerts
   - Review usage monthly
   - Optimize inefficient code
