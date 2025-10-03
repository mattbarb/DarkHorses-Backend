#!/usr/bin/env python3
"""
Historical Odds Cron Scheduler with Intelligent Backfill
On first run: Aggressively backfills from 2015 to current date
After backfill complete: Runs daily at 1:00 AM UK time

Flow:
1. Check backfill state
2. If incomplete: Run aggressive backfill (100 dates per cycle)
3. If complete: Switch to daily 1 AM schedule
4. Update monitoring dashboard with real-time progress
"""

import os
import sys
import logging
import time
import json
from datetime import datetime, timedelta, date
import pytz
from typing import Optional, Dict
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from historical_odds_fetcher import HistoricalOddsFetcher
from historical_odds_client import HistoricalOddsClient
from backfill_historical import HistoricalBackfill
from schema_mapping import SchemaMapper

# Setup logging FIRST (before using logger anywhere)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cron_historical.log')
    ]
)
logger = logging.getLogger(__name__)

# Import monitor (optional)
try:
    from monitor_server import start_monitor_server, update_stats, add_activity
    MONITOR_ENABLED = True
    logger.info("✅ Monitor server module imported successfully")
except ImportError as e:
    logger.error(f"❌ Monitor server not available: {e}")
    MONITOR_ENABLED = False
    def start_monitor_server(*args, **kwargs):
        logger.warning("Monitor server disabled - start_monitor_server called")
    def update_stats(*args, **kwargs):
        logger.debug(f"Monitor disabled - update_stats called with: {kwargs}")
    def add_activity(*args, **kwargs):
        logger.debug(f"Monitor disabled - add_activity called")

# UK timezone for scheduling
UK_TZ = pytz.timezone('Europe/London')

# State file for tracking backfill progress
STATE_FILE = Path(__file__).parent / 'backfill_state.json'


class HistoricalOddsScheduler:
    """Daily scheduler for historical odds fetching"""

    def __init__(self, start_year: int = 2015):
        """Initialize scheduler with monitoring"""
        self.fetcher = HistoricalOddsFetcher()
        self.client = HistoricalOddsClient()
        self.backfill = HistoricalBackfill(start_year=start_year)
        self.mapper = SchemaMapper()

        self.start_year = start_year
        self.last_run = None

        # Disable monitor server in production worker mode
        MONITOR_ENABLED_ENV = os.getenv('MONITOR_ENABLED', 'false').lower() == 'true'

        if MONITOR_ENABLED and MONITOR_ENABLED_ENV:
            logger.info("🌐 Starting monitor server on port 5001...")
            start_monitor_server(port=5001)
            logger.info("✅ Monitor server started on port 5001")
            logger.info("📊 Updating initial stats...")
            update_stats(status='backfilling', backfill_start_year=self.start_year)
            add_activity("Historical odds scheduler initialized")
            logger.info("✅ Monitor initialized and ready")
        else:
            logger.info("⚠️ Monitor server disabled (Render.com worker mode)")

        # Load backfill state
        self.state = self.load_state()

        # Calculate total dates to process
        self.total_dates = (date.today() - date(start_year, 1, 1)).days + 1

        logger.info(f"Scheduler initialized: Start year {start_year}, Total dates to process: {self.total_dates}")

    def load_state(self) -> Dict:
        """Load backfill state from file"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                    logger.info(f"Loaded state: {state.get('dates_processed', 0)} dates processed")
                    return state
            except Exception as e:
                logger.error(f"Error loading state: {e}")

        # Default state for first run
        return {
            'backfill_complete': False,
            'dates_processed': 0,
            'last_date_processed': None,
            'started_at': datetime.now(UK_TZ).isoformat(),
            'completed_at': None
        }

    def save_state(self):
        """Save backfill state to file"""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def is_backfill_complete(self) -> bool:
        """Check if backfill is complete"""
        if self.state.get('backfill_complete'):
            return True

        # Check database to see actual progress
        existing_dates = self.client.get_existing_dates()
        dates_processed = len(existing_dates)

        # Consider complete if we have 95% of expected dates (allow for some missing races)
        completion_threshold = self.total_dates * 0.95
        is_complete = dates_processed >= completion_threshold

        if is_complete and not self.state.get('backfill_complete'):
            logger.info(f"✅ Backfill complete! {dates_processed} of {self.total_dates} dates processed")
            self.state['backfill_complete'] = True
            self.state['completed_at'] = datetime.now(UK_TZ).isoformat()
            self.save_state()

            if MONITOR_ENABLED:
                update_stats(
                    status='running',
                    backfill_progress_percent=100,
                    dates_processed=dates_processed,
                    dates_remaining=0
                )
                add_activity("🎉 Backfill complete! Switching to daily schedule")

        return is_complete

    def fetch_yesterday(self) -> bool:
        """Fetch yesterday's completed races"""
        try:
            # Get yesterday's date in UK timezone
            yesterday = (datetime.now(UK_TZ) - timedelta(days=1)).date()
            date_str = yesterday.strftime('%Y-%m-%d')

            logger.info(f"📅 Fetching odds for yesterday: {date_str}")

            # Fetch complete runner data (racecards + results)
            logger.info(f"  📡 Fetching data from Racing API...")
            runner_records = self.fetcher.fetch_complete_date_data(date_str, regions=['gb', 'ire'])

            if not runner_records:
                logger.info(f"  ⚠️  No data found for {date_str}")
                return True

            logger.info(f"  📊 Found {len(runner_records)} runner records")

            # Map to database schema
            logger.info(f"  🗺️  Mapping {len(runner_records)} records to database schema...")
            mapped_records = self.mapper.map_batch(runner_records)

            if not mapped_records:
                logger.warning(f"  ⚠️  No records mapped successfully for {date_str}")
                return False

            logger.info(f"  ✅ Mapped {len(mapped_records)} records")

            # Store in database
            logger.info(f"  💾 Storing {len(mapped_records)} records in database...")
            total_stored = 0
            for record in mapped_records:
                try:
                    success = self.client.upsert_odds(record)
                    if success:
                        total_stored += 1
                except Exception as e:
                    logger.error(f"  ❌ Error storing record: {e}")

            logger.info(f"  ✅ Successfully stored {total_stored}/{len(mapped_records)} records for {date_str}")

            if MONITOR_ENABLED:
                update_stats(
                    races_processed_today=len(set(r.get('race_id') for r in mapped_records if r.get('race_id'))),
                    odds_stored_today=total_stored
                )
                add_activity(f"Daily update: {total_stored} odds stored for {date_str}")
            return True

        except Exception as e:
            logger.error(f"Error fetching yesterday's data: {e}")
            return False

    def run_aggressive_backfill(self, dates_per_cycle: int = 100) -> Dict:
        """
        Run aggressive backfill for initial data population
        Processes many dates quickly to catch up from 2015
        """
        try:
            logger.info("=" * 80)
            logger.info(f"🚀 AGGRESSIVE BACKFILL MODE")
            logger.info(f"Processing up to {dates_per_cycle} dates per cycle")
            logger.info("=" * 80)

            if MONITOR_ENABLED:
                update_stats(status='backfilling')
                add_activity(f"Starting aggressive backfill ({dates_per_cycle} dates)")

            # Get missing dates
            start_date_str = f"{self.start_year}-01-01"
            end_date_str = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
            missing_dates = self.client.get_missing_dates(start_date_str, end_date_str)

            logger.info(f"Found {len(missing_dates)} missing dates")

            if not missing_dates:
                logger.info("✅ No missing dates! Backfill complete")
                return {'dates_processed': 0, 'races_processed': 0, 'odds_stored': 0}

            # Process dates (limited to dates_per_cycle)
            dates_to_process = missing_dates[:dates_per_cycle]
            total_races = 0
            total_odds = 0
            successful_dates = 0

            for i, process_date in enumerate(dates_to_process, 1):
                try:
                    logger.info(f"[{i}/{len(dates_to_process)}] Processing {process_date}")

                    if MONITOR_ENABLED:
                        # Update progress
                        existing = self.client.get_existing_dates()
                        dates_processed = len(existing)
                        dates_remaining = self.total_dates - dates_processed
                        progress = (dates_processed / self.total_dates) * 100

                        update_stats(
                            status='backfilling',
                            backfill_current_date=process_date,
                            dates_processed=dates_processed,
                            dates_remaining=dates_remaining,
                            backfill_progress_percent=round(progress, 1),
                            current_operation=f"Processing {process_date} ({i}/{len(dates_to_process)})"
                        )

                    # Fetch complete runner data for this date (with pre-race odds + results)
                    logger.info(f"  📡 Fetching data from Racing API...")
                    runner_records = self.fetcher.fetch_complete_date_data(process_date, regions=['gb', 'ire'])

                    if not runner_records:
                        logger.info(f"  ⚠️  No data found for {process_date}")
                        continue

                    logger.info(f"  📊 Found {len(runner_records)} runner records")

                    # Map runner records to database schema
                    logger.info(f"  🗺️  Mapping {len(runner_records)} records to database schema...")
                    mapped_records = self.mapper.map_batch(runner_records)

                    if not mapped_records:
                        logger.warning(f"  ⚠️  No records mapped successfully for {process_date}")
                        continue

                    logger.info(f"  ✅ Mapped {len(mapped_records)} records")

                    # Store in database
                    logger.info(f"  💾 Storing {len(mapped_records)} records in database...")
                    stored_count = 0
                    for record in mapped_records:
                        try:
                            success = self.client.upsert_odds(record)
                            if success:
                                stored_count += 1
                        except Exception as e:
                            logger.error(f"  ❌ Error storing record: {e}")

                    logger.info(f"  ✅ Successfully stored {stored_count}/{len(mapped_records)} records")

                    total_odds += stored_count
                    total_races += len(set(r.get('race_id') for r in mapped_records if r.get('race_id')))
                    successful_dates += 1

                    # Update state
                    self.state['dates_processed'] = successful_dates
                    self.state['last_date_processed'] = process_date
                    self.save_state()

                    # Small delay to avoid rate limiting
                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error processing date {process_date}: {e}")

            # Update monitoring
            if MONITOR_ENABLED:
                add_activity(f"Completed cycle: {successful_dates} dates, {total_races} races, {total_odds} odds")

            logger.info(f"✅ Backfill cycle complete: {successful_dates} dates, {total_races} races, {total_odds} odds")

            return {
                'dates_processed': successful_dates,
                'races_processed': total_races,
                'odds_stored': total_odds
            }

        except Exception as e:
            logger.error(f"Error in aggressive backfill: {e}")
            return {'dates_processed': 0, 'races_processed': 0, 'odds_stored': 0}

    def run_backfill_chunk(self, max_dates: int = 10) -> bool:
        """Run a small chunk of backfill (used in daily mode)"""
        try:
            logger.info(f"Running backfill chunk (max {max_dates} dates)...")

            # Get missing dates
            start_date_str = f"{self.start_year}-01-01"
            end_date_str = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
            missing_dates = self.client.get_missing_dates(start_date_str, end_date_str)

            if not missing_dates:
                logger.info("No missing dates to backfill")
                return True

            # Process small chunk
            stats = self.run_aggressive_backfill(dates_per_cycle=max_dates)

            logger.info(
                f"Backfill chunk complete: "
                f"{stats.get('dates_processed', 0)} dates, "
                f"{stats.get('races_processed', 0)} races, "
                f"{stats.get('odds_stored', 0)} odds stored"
            )

            return True

        except Exception as e:
            logger.error(f"Error in backfill chunk: {e}")
            return False

    def run_daily_job(self):
        """Run the daily scheduled job"""
        logger.info("=" * 80)
        logger.info("Starting daily historical odds job")
        logger.info(f"Run time: {datetime.now(UK_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info("=" * 80)

        try:
            # Step 1: Fetch yesterday's races
            logger.info("\n--- STEP 1: Fetching yesterday's races ---")
            yesterday_success = self.fetch_yesterday()

            if not yesterday_success:
                logger.error("Failed to fetch yesterday's data")

            # Step 2: Run backfill chunk
            logger.info("\n--- STEP 2: Running backfill chunk ---")
            backfill_success = self.run_backfill_chunk(max_dates=10)

            if not backfill_success:
                logger.error("Failed to run backfill chunk")

            # Update last run time
            self.last_run = datetime.now(UK_TZ)

            logger.info("\n" + "=" * 80)
            logger.info("Daily job complete")
            logger.info(f"Next run scheduled for: {self.get_next_run_time()}")
            logger.info("=" * 80 + "\n")

        except Exception as e:
            logger.error(f"Error in daily job: {e}")

    def get_next_run_time(self) -> datetime:
        """Calculate next run time (1 AM UK time)"""
        now = datetime.now(UK_TZ)
        next_run = now.replace(hour=1, minute=0, second=0, microsecond=0)

        # If it's already past 1 AM today, schedule for tomorrow
        if now.hour >= 1:
            next_run += timedelta(days=1)

        return next_run

    def seconds_until_next_run(self) -> int:
        """Calculate seconds until next scheduled run"""
        next_run = self.get_next_run_time()
        now = datetime.now(UK_TZ)
        delta = next_run - now
        return int(delta.total_seconds())

    def run_continuous(self):
        """
        Run scheduler continuously with intelligent backfill
        Phase 1: Aggressive backfill from 2015 to current (if incomplete)
        Phase 2: Daily execution at 1 AM UK time (after backfill complete)
        """
        logger.info("=" * 80)
        logger.info("🚀 STARTING HISTORICAL ODDS SCHEDULER")
        logger.info("=" * 80)
        logger.info(f"Start year: {self.start_year}")
        logger.info(f"Total dates to process: {self.total_dates}")
        logger.info(f"Backfill complete: {self.state.get('backfill_complete', False)}")
        logger.info("⚡ SERVICE WILL START PROCESSING IMMEDIATELY")
        logger.info("=" * 80)

        # PHASE 1: Initial Backfill (if not complete)
        if not self.is_backfill_complete():
            logger.info("\n📊 PHASE 1: AGGRESSIVE BACKFILL")
            logger.info("Will process all dates from 2015 to current date")
            logger.info("This will continue until caught up, then switch to daily mode")
            logger.info("=" * 80)

            if MONITOR_ENABLED:
                update_stats(
                    status='backfilling',
                    current_operation='Starting initial backfill from 2015'
                )
                add_activity("🚀 Starting aggressive backfill from 2015")

            # Run aggressive backfill cycles until complete
            cycle_count = 0
            while not self.is_backfill_complete():
                cycle_count += 1
                logger.info(f"\n🔄 BACKFILL CYCLE {cycle_count}")

                try:
                    # Process 100 dates per cycle (adjust based on rate limits)
                    stats = self.run_aggressive_backfill(dates_per_cycle=100)

                    if stats['dates_processed'] == 0:
                        # No more missing dates
                        logger.info("✅ No more missing dates found!")
                        break

                    logger.info(
                        f"Cycle {cycle_count} complete: "
                        f"{stats['dates_processed']} dates, "
                        f"{stats['races_processed']} races, "
                        f"{stats['odds_stored']} odds"
                    )

                    # Check if complete
                    if self.is_backfill_complete():
                        logger.info("\n" + "=" * 80)
                        logger.info("🎉 BACKFILL COMPLETE!")
                        logger.info("=" * 80)
                        break

                    # Brief pause between cycles
                    logger.info("Pausing 30 seconds before next cycle...")
                    time.sleep(30)

                except Exception as e:
                    logger.error(f"Error in backfill cycle {cycle_count}: {e}")
                    logger.info("Waiting 5 minutes before retry...")
                    time.sleep(300)

            logger.info("\n" + "=" * 80)
            logger.info("✅ BACKFILL PHASE COMPLETE")
            logger.info("Switching to daily maintenance mode...")
            logger.info("=" * 80 + "\n")

        # PHASE 2: Daily Maintenance Mode
        logger.info("\n📅 PHASE 2: DAILY MAINTENANCE MODE")
        logger.info("Running daily at 1:00 AM UK time")
        logger.info(f"Next scheduled run: {self.get_next_run_time()}")
        logger.info("=" * 80)

        if MONITOR_ENABLED:
            update_stats(
                status='running',
                current_operation='Waiting for next daily run at 1 AM UK time'
            )
            add_activity("✅ Switched to daily maintenance mode (1 AM UK)")

        # Continuous daily loop
        while True:
            try:
                # Calculate sleep time until next run
                sleep_seconds = self.seconds_until_next_run()
                next_run = self.get_next_run_time()

                logger.info(f"\n⏰ Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                logger.info(f"Sleeping for {sleep_seconds/3600:.1f} hours...")

                if MONITOR_ENABLED:
                    update_stats(
                        status='waiting',
                        current_operation=f'Next run: {next_run.strftime("%Y-%m-%d %H:%M %Z")}'
                    )

                time.sleep(sleep_seconds)

                # Run daily job
                logger.info("\n🔔 Daily job triggered!")
                self.run_daily_job()

            except KeyboardInterrupt:
                logger.info("\n❌ Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {e}")
                logger.info("Waiting 1 hour before retry...")
                if MONITOR_ENABLED:
                    add_activity(f"Error in scheduler: {str(e)[:100]}")
                time.sleep(3600)

    def run_once(self):
        """Run the job once (for testing or manual execution)"""
        self.run_daily_job()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Historical Odds Scheduler')
    parser.add_argument(
        '--start-year',
        type=int,
        default=2015,
        help='Start year for backfill (default: 2015)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (for testing)'
    )

    args = parser.parse_args()

    scheduler = HistoricalOddsScheduler(start_year=args.start_year)

    if args.once:
        logger.info("Running in single-execution mode")
        scheduler.run_once()
    else:
        logger.info("Running in continuous mode")
        scheduler.run_continuous()


if __name__ == '__main__':
    main()
