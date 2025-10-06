# Legacy Monolithic Code (Archived)

This directory contains the **old monolithic architecture** that has been replaced by the microservices structure.

## Status: DEPRECATED - DO NOT USE

This code is kept for reference and as a rollback option only. It is **not deployed** and should **not be modified**.

## What Was This?

The original "all-in-one" architecture that ran:
- FastAPI server (API + Dashboard UI)
- Live odds scheduler
- Historical odds scheduler
- Statistics updater

All in a single process via `start.py`.

## What Replaced It?

**New Microservices Architecture (Active)**:
- `../workers/` - Background data collection service (no HTTP)
- `../api/` - Read-only HTTP API + dashboard UI

See `../MICROSERVICES_ARCHITECTURE.md` for details.

## Rollback Instructions

If you need to rollback to the monolithic architecture:

1. **Rename directory back**:
   ```bash
   git mv _legacy_monolithic odds_api
   ```

2. **Update render.yaml**:
   ```yaml
   services:
     - type: web
       name: darkhorses-odds-api
       env: python
       plan: starter
       rootDir: odds_api
       buildCommand: pip install -r requirements.txt
       startCommand: python3 start.py
   ```

3. **Push and redeploy**:
   ```bash
   git commit -m "Rollback to monolithic architecture"
   git push
   ```

4. **In Render Dashboard**:
   - Suspend the two microservices (workers + api)
   - Deploy the monolithic service from odds_api/

## Files in This Directory

- `start.py` - Main entry point (runs API + schedulers)
- `main.py` - FastAPI application
- `scheduler.py` - Consolidated scheduler
- `live_odds/` - Live odds fetching
- `historical_odds/` - Historical odds fetching
- `odds_statistics/` - Statistics tracking
- `static/` - Dashboard UI

All of these have been moved to `../workers/` or `../api/` in the new architecture.

## Last Active

This monolithic architecture was active until October 6, 2025, when it was replaced by the microservices architecture.

---

**For current documentation, see**:
- `../MICROSERVICES_ARCHITECTURE.md` - New architecture overview
- `../workers/` - Workers service
- `../api/` - API service
