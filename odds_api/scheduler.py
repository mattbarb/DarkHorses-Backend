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
from datetime import datetime, timedelta, time as dt_time
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

logger = logging.getLogger('SCHEDULER')  # Clear service name

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
        """Run live odds fetch cycle and return next interval"""
        self.status["live_odds"]["last_run"] = datetime.now().isoformat()
        self.status["live_odds"]["status"] = "running"
        self._save_status()

        try:
            logger.info("🏇 Starting live odds fetch cycle...")
            if not self.live_scheduler:
                self.live_scheduler = LiveOddsScheduler()

            # Run fetch cycle
            self.live_scheduler.run_fetch_cycle()

            # Get next optimal interval based on race proximity
            races = self.live_scheduler.get_upcoming_races()
            next_interval_seconds, reason = self.live_scheduler.get_optimal_interval(races)

            logger.info("✅ Live odds fetch cycle completed")
            logger.info(f"⏱️  Next check in {next_interval_seconds}s - {reason}")

            self.status["live_odds"]["last_success"] = datetime.now().isoformat()
            self.status["live_odds"]["status"] = "success"
            self.status["live_odds"]["next_check"] = reason
            self.status["live_odds"]["next_interval"] = next_interval_seconds
            self._save_status()

            return next_interval_seconds

        except Exception as e:
            logger.error(f"❌ Live odds fetch failed: {e}")
            self.status["live_odds"]["status"] = "failed"
            self.status["live_odds"]["error"] = str(e)
            self._save_status()
            # Return default interval on error
            return 300  # 5 minutes

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

        # Historical odds - daily at 1:00 AM UK time
        schedule.every().day.at("01:00").do(self.run_historical_odds)
        logger.info("📅 Scheduled: Historical odds daily at 1:00 AM")

        # Statistics - every 10 minutes
        schedule.every(10).minutes.do(self.run_statistics_update)
        logger.info("📅 Scheduled: Statistics update every 10 minutes")

        # Note: Live odds uses adaptive scheduling in run() method
        logger.info("📅 Scheduled: Live odds with adaptive intervals")
        logger.info("   - 10s when race imminent (<5 min)")
        logger.info("   - 60s when race soon (<30 min)")
        logger.info("   - 5 min when race upcoming (<2 hours)")
        logger.info("   - 15 min default check interval")

        # Run initial fetch on startup
        logger.info("🚀 Running initial fetch on startup...")
        self.run_live_odds()
        self.run_statistics_update()

    def run(self):
        """Start the scheduler loop with adaptive live odds scheduling"""
        self.running = True
        self.setup_schedules()

        logger.info("✅ Consolidated scheduler started successfully")
        logger.info("📋 Active schedules:")
        logger.info("   - Live odds: ADAPTIVE (10s-15min based on race proximity)")
        logger.info("   - Historical odds: Daily at 1:00 AM UK time")
        logger.info("   - Statistics: Every 10 minutes")

        # Track next live odds check time
        next_live_check = datetime.now()

        while self.running:
            try:
                # Run fixed schedules (historical, statistics)
                schedule.run_pending()

                # Handle adaptive live odds scheduling
                now = datetime.now()
                if now >= next_live_check:
                    # Run live odds and get next interval
                    next_interval_seconds = self.run_live_odds()

                    # Schedule next check
                    next_live_check = now + timedelta(seconds=next_interval_seconds)
                    logger.info(f"📅 Next live odds check at: {next_live_check.strftime('%H:%M:%S')}")

                time.sleep(1)

            except KeyboardInterrupt:
                logger.info("⏹️  Scheduler stopped by user")
                self.running = False
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
                # On error, try again in 5 minutes
                next_live_check = datetime.now() + timedelta(minutes=5)
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
