#!/usr/bin/env python3
"""
Consolidated Scheduler
Runs all background tasks: live odds, historical odds, and statistics updates
"""

import sys
import os
import threading
import time
import logging
from datetime import datetime, time as dt_time
from pathlib import Path
import schedule

# Import scheduler modules
from live_odds.cron_live import LiveOddsScheduler
from historical_odds.cron_historical import HistoricalOddsScheduler
from odds_statistics.update_stats import update_all_statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / 'logs' / 'scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ConsolidatedScheduler:
    """Runs all schedulers in a single process"""

    def __init__(self):
        self.running = False
        self.live_scheduler = None
        self.historical_scheduler = None

    def run_live_odds(self):
        """Run live odds fetch cycle"""
        try:
            logger.info("🏇 Starting live odds fetch cycle...")
            self.live_scheduler = LiveOddsScheduler()
            self.live_scheduler.run_fetch_cycle()
            logger.info("✅ Live odds fetch cycle completed")
        except Exception as e:
            logger.error(f"❌ Live odds fetch failed: {e}")

    def run_historical_odds(self):
        """Run historical odds daily fetch"""
        try:
            logger.info("📚 Starting historical odds daily fetch...")
            self.historical_scheduler = HistoricalOddsScheduler()
            self.historical_scheduler.run_daily_job()
            logger.info("✅ Historical odds daily fetch completed")
        except Exception as e:
            logger.error(f"❌ Historical odds fetch failed: {e}")

    def run_statistics_update(self):
        """Run statistics update for all tables"""
        try:
            logger.info("📊 Updating statistics...")
            update_all_statistics(save_to_file=True)
            logger.info("✅ Statistics updated successfully")
        except Exception as e:
            logger.warning(f"⚠️  Statistics update failed (non-critical): {e}")
            if "Network is unreachable" in str(e):
                logger.warning("💡 Hint: Render.com may not support IPv6. Consider using Supabase SDK for statistics.")

    def setup_schedules(self):
        """Configure all scheduled tasks"""

        # Live odds - every 5 minutes
        schedule.every(5).minutes.do(self.run_live_odds)
        logger.info("📅 Scheduled: Live odds every 5 minutes")

        # Historical odds - daily at 1:00 AM UK time
        schedule.every().day.at("01:00").do(self.run_historical_odds)
        logger.info("📅 Scheduled: Historical odds daily at 1:00 AM")

        # Statistics - every 10 minutes (after live odds cycles)
        schedule.every(10).minutes.do(self.run_statistics_update)
        logger.info("📅 Scheduled: Statistics update every 10 minutes")

        # Run initial fetch on startup
        logger.info("🚀 Running initial fetch on startup...")
        self.run_live_odds()
        self.run_statistics_update()

    def run(self):
        """Start the scheduler loop"""
        self.running = True
        self.setup_schedules()

        logger.info("✅ Consolidated scheduler started successfully")
        logger.info("📋 Active schedules:")
        logger.info("   - Live odds: Every 5 minutes")
        logger.info("   - Historical odds: Daily at 1:00 AM UK time")
        logger.info("   - Statistics: Every 10 minutes")

        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("⏹️  Scheduler stopped by user")
                self.running = False
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
                time.sleep(5)

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("🛑 Scheduler stopping...")


def run_scheduler_background():
    """Run scheduler in background thread"""
    scheduler = ConsolidatedScheduler()
    scheduler.run()


if __name__ == "__main__":
    # Create logs directory
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    # Run scheduler
    scheduler = ConsolidatedScheduler()
    scheduler.run()
