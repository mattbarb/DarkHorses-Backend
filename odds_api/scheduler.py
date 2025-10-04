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
import json
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
        self.status_file = Path(__file__).parent / 'logs' / 'scheduler_status.json'

        # Initialize status tracking
        self.status = {
            "live_odds": {"last_run": None, "last_success": None, "status": "idle"},
            "historical_odds": {"last_run": None, "last_success": None, "status": "idle"},
            "statistics": {"last_run": None, "last_success": None, "status": "idle"}
        }
        self._load_status()

    def _load_status(self):
        """Load status from file if it exists"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    self.status = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load status file: {e}")

    def _save_status(self):
        """Save status to file"""
        try:
            self.status_file.parent.mkdir(exist_ok=True)
            with open(self.status_file, 'w') as f:
                json.dump(self.status, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save status file: {e}")

    def run_live_odds(self):
        """Run live odds fetch cycle"""
        self.status["live_odds"]["last_run"] = datetime.now().isoformat()
        self.status["live_odds"]["status"] = "running"
        self._save_status()

        try:
            logger.info("🏇 Starting live odds fetch cycle...")
            self.live_scheduler = LiveOddsScheduler()
            self.live_scheduler.run_fetch_cycle()
            logger.info("✅ Live odds fetch cycle completed")

            self.status["live_odds"]["last_success"] = datetime.now().isoformat()
            self.status["live_odds"]["status"] = "success"
            self._save_status()
        except Exception as e:
            logger.error(f"❌ Live odds fetch failed: {e}")
            self.status["live_odds"]["status"] = "failed"
            self.status["live_odds"]["error"] = str(e)
            self._save_status()

    def run_historical_odds(self):
        """Run historical odds daily fetch"""
        self.status["historical_odds"]["last_run"] = datetime.now().isoformat()
        self.status["historical_odds"]["status"] = "running"
        self._save_status()

        try:
            logger.info("📚 Starting historical odds daily fetch...")
            self.historical_scheduler = HistoricalOddsScheduler()
            self.historical_scheduler.run_daily_job()
            logger.info("✅ Historical odds daily fetch completed")

            self.status["historical_odds"]["last_success"] = datetime.now().isoformat()
            self.status["historical_odds"]["status"] = "success"
            self._save_status()
        except Exception as e:
            logger.error(f"❌ Historical odds fetch failed: {e}")
            self.status["historical_odds"]["status"] = "failed"
            self.status["historical_odds"]["error"] = str(e)
            self._save_status()

    def run_statistics_update(self):
        """Run statistics update for all tables"""
        self.status["statistics"]["last_run"] = datetime.now().isoformat()
        self.status["statistics"]["status"] = "running"
        self._save_status()

        try:
            logger.info("📊 Updating statistics...")
            update_all_statistics(save_to_file=True)
            logger.info("✅ Statistics updated successfully")

            self.status["statistics"]["last_success"] = datetime.now().isoformat()
            self.status["statistics"]["status"] = "success"
            self._save_status()
        except Exception as e:
            logger.error(f"❌ Statistics update failed: {e}")
            self.status["statistics"]["status"] = "failed"
            self.status["statistics"]["error"] = str(e)
            self._save_status()

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
