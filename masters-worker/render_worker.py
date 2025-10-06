#!/usr/bin/env python3
"""
Render.com Worker - Scheduled Racing API Data Fetcher
Runs as a long-running worker process with scheduled tasks
"""

import sys
import time
import schedule
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from config.config import get_config
from utils.logger import get_logger
from main import ReferenceDataOrchestrator

logger = get_logger('render_worker')


def run_daily_fetch():
    """Run daily fetch: races and results"""
    logger.info("=" * 80)
    logger.info(f"DAILY FETCH TRIGGERED - {datetime.utcnow().isoformat()}")
    logger.info("=" * 80)

    try:
        orchestrator = ReferenceDataOrchestrator()
        results = orchestrator.run_fetch(entities=['races', 'results'])

        success = all(r.get('success', False) for r in results.values())
        if success:
            logger.info("Daily fetch completed successfully")
        else:
            logger.error("Daily fetch completed with errors")

    except Exception as e:
        logger.error(f"Daily fetch failed: {e}", exc_info=True)


def run_weekly_fetch():
    """Run weekly fetch: people and horses"""
    logger.info("=" * 80)
    logger.info(f"WEEKLY FETCH TRIGGERED - {datetime.utcnow().isoformat()}")
    logger.info("=" * 80)

    try:
        orchestrator = ReferenceDataOrchestrator()
        results = orchestrator.run_fetch(
            entities=['jockeys', 'trainers', 'owners', 'horses']
        )

        success = all(r.get('success', False) for r in results.values())
        if success:
            logger.info("Weekly fetch completed successfully")
        else:
            logger.error("Weekly fetch completed with errors")

    except Exception as e:
        logger.error(f"Weekly fetch failed: {e}", exc_info=True)


def run_monthly_fetch():
    """Run monthly fetch: courses and bookmakers"""
    logger.info("=" * 80)
    logger.info(f"MONTHLY FETCH TRIGGERED - {datetime.utcnow().isoformat()}")
    logger.info("=" * 80)

    try:
        orchestrator = ReferenceDataOrchestrator()
        results = orchestrator.run_fetch(
            entities=['courses', 'bookmakers']
        )

        success = all(r.get('success', False) for r in results.values())
        if success:
            logger.info("Monthly fetch completed successfully")
        else:
            logger.error("Monthly fetch completed with errors")

    except Exception as e:
        logger.error(f"Monthly fetch failed: {e}", exc_info=True)


def run_initial_sync():
    """Run initial full sync on first startup"""
    logger.info("=" * 80)
    logger.info("INITIAL SYNC - Fetching all entities")
    logger.info("=" * 80)

    try:
        orchestrator = ReferenceDataOrchestrator()
        results = orchestrator.run_fetch(entities=None)  # Fetch all

        success = all(r.get('success', False) for r in results.values())
        if success:
            logger.info("Initial sync completed successfully")
        else:
            logger.error("Initial sync completed with errors")

    except Exception as e:
        logger.error(f"Initial sync failed: {e}", exc_info=True)


def main():
    """Main worker process"""
    logger.info("=" * 80)
    logger.info("RACING API MASTERS - RENDER WORKER")
    logger.info(f"Started at: {datetime.utcnow().isoformat()}")
    logger.info("=" * 80)

    # Run initial sync on startup (optional - comment out if not needed)
    # logger.info("\nRunning initial sync...")
    # run_initial_sync()

    # Schedule jobs
    logger.info("\nScheduling jobs...")

    # Daily: 1:00 AM UTC
    schedule.every().day.at("01:00").do(run_daily_fetch)
    logger.info("  ✓ Daily fetch: 01:00 UTC (races, results)")

    # Weekly: Sunday 2:00 AM UTC
    schedule.every().sunday.at("02:00").do(run_weekly_fetch)
    logger.info("  ✓ Weekly fetch: Sunday 02:00 UTC (jockeys, trainers, owners, horses)")

    # Monthly: 1st day at 3:00 AM UTC (approximated with weekly check)
    schedule.every().monday.at("03:00").do(
        lambda: run_monthly_fetch() if datetime.utcnow().day <= 7 else None
    )
    logger.info("  ✓ Monthly fetch: First Monday 03:00 UTC (courses, bookmakers)")

    logger.info("\nWorker running. Press Ctrl+C to stop.")
    logger.info("=" * 80)

    # Keep worker running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        logger.info("\nWorker stopped by user")
    except Exception as e:
        logger.error(f"Worker crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
