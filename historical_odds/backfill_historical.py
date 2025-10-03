#!/usr/bin/env python3
"""
Historical Odds Backfill Script for Production (Render.com)
Fetches all historical racing odds from 2015 to current date
Designed to run continuously and keep the database updated
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Tuple
import argparse
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from historical_odds_fetcher import HistoricalOddsFetcher
from historical_odds_client import HistoricalOddsClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backfill_historical.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

class HistoricalBackfill:
    """Manages backfilling of historical odds data from 2015 onwards"""

    def __init__(self, start_year: int = 2015):
        """Initialize backfill manager"""
        self.start_year = start_year
        self.fetcher = HistoricalOddsFetcher()
        self.client = HistoricalOddsClient()
        self.batch_size = 7  # Process 7 days at a time
        self.delay_between_batches = 5  # Seconds between batches
        self.daily_limit = 100  # Max days to process per run (to avoid rate limits)

    def get_date_ranges(self) -> List[Tuple[date, date]]:
        """Get list of date ranges to process"""
        ranges = []

        # Start from beginning of start_year
        start_date = date(self.start_year, 1, 1)
        end_date = date.today() - timedelta(days=1)  # Yesterday

        # Create weekly ranges
        current_date = start_date
        while current_date <= end_date:
            batch_end = min(current_date + timedelta(days=self.batch_size - 1), end_date)
            ranges.append((current_date, batch_end))
            current_date = batch_end + timedelta(days=1)

        return ranges

    def check_existing_dates(self) -> set:
        """Check which dates already have data in database"""
        try:
            existing = self.client.get_existing_dates()
            logger.info(f"Found {len(existing)} dates with existing data")
            return existing
        except Exception as e:
            logger.error(f"Error checking existing dates: {e}")
            return set()

    def process_date(self, process_date: date) -> bool:
        """Process a single date"""
        try:
            logger.info(f"Processing {process_date}")

            # Fetch odds data
            odds_data = self.fetcher.fetch_historical_odds(
                target_date=process_date.strftime('%Y-%m-%d')
            )

            if not odds_data:
                logger.info(f"No data for {process_date}")
                return True

            # Store in database
            stats = self.client.bulk_insert(odds_data)

            logger.info(
                f"Date {process_date}: "
                f"Inserted {stats.get('inserted', 0)}, "
                f"Updated {stats.get('updated', 0)}, "
                f"Errors {stats.get('errors', 0)}"
            )

            return stats.get('errors', 0) == 0

        except Exception as e:
            logger.error(f"Error processing {process_date}: {e}")
            return False

    def process_date_range(self, start_date: date, end_date: date, skip_existing: bool = True) -> dict:
        """Process a range of dates"""
        stats = {
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'total_records': 0
        }

        # Get existing dates if skipping
        existing_dates = self.check_existing_dates() if skip_existing else set()

        # Process each date in range
        current_date = start_date
        while current_date <= end_date:
            # Check if date already processed
            if skip_existing and current_date in existing_dates:
                logger.info(f"Skipping {current_date} - already processed")
                stats['skipped'] += 1
            else:
                # Process the date
                success = self.process_date(current_date)

                if success:
                    stats['processed'] += 1
                else:
                    stats['errors'] += 1

                # Rate limiting
                time.sleep(2)  # 2 seconds between dates

            current_date += timedelta(days=1)

        return stats

    def run_backfill(self, resume: bool = True, max_days: int = None):
        """Run the backfill process"""
        logger.info("=" * 60)
        logger.info("HISTORICAL ODDS BACKFILL")
        logger.info("=" * 60)
        logger.info(f"Start year: {self.start_year}")
        logger.info(f"Resume mode: {resume}")

        # Get all date ranges
        all_ranges = self.get_date_ranges()
        total_ranges = len(all_ranges)
        logger.info(f"Total date ranges to process: {total_ranges}")

        # Limit processing if specified
        if max_days:
            days_to_process = max_days
        else:
            days_to_process = self.daily_limit

        days_processed = 0

        # Process each range
        for i, (start_date, end_date) in enumerate(all_ranges, 1):
            if days_processed >= days_to_process:
                logger.info(f"Reached daily limit of {days_to_process} days")
                break

            logger.info(f"\nProcessing range {i}/{total_ranges}: {start_date} to {end_date}")

            # Process the range
            stats = self.process_date_range(start_date, end_date, skip_existing=resume)

            days_processed += stats['processed'] + stats['skipped']

            logger.info(
                f"Range complete: "
                f"Processed {stats['processed']}, "
                f"Skipped {stats['skipped']}, "
                f"Errors {stats['errors']}"
            )

            # Delay between ranges
            if i < total_ranges:
                time.sleep(self.delay_between_batches)

        logger.info("\n" + "=" * 60)
        logger.info("BACKFILL COMPLETE")
        logger.info(f"Total days processed: {days_processed}")
        logger.info("=" * 60)

    def run_daily_update(self):
        """Run daily update for recent dates to ensure no gaps"""
        logger.info("Running daily update...")

        # Check last 7 days to catch any missed dates
        end_date = date.today() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=6)  # 7 days ago

        logger.info(f"Checking dates from {start_date} to {end_date}")

        # Skip existing should be True for daily updates to avoid re-processing
        stats = self.process_date_range(start_date, end_date, skip_existing=True)

        logger.info(
            f"Daily update complete: "
            f"Processed {stats['processed']}, "
            f"Skipped {stats['skipped']}, "
            f"Errors {stats['errors']}"
        )

        return stats

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Backfill historical racing odds data')
    parser.add_argument('--start-year', type=int, default=2015,
                        help='Start year for backfill (default: 2015)')
    parser.add_argument('--daily-update', action='store_true',
                        help='Run daily update mode (last 7 days)')
    parser.add_argument('--no-resume', action='store_true',
                        help='Process all dates even if they exist')
    parser.add_argument('--max-days', type=int,
                        help='Maximum days to process in one run')
    parser.add_argument('--continuous', action='store_true',
                        help='Run continuously with daily updates')

    args = parser.parse_args()

    # Create backfill manager
    backfill = HistoricalBackfill(start_year=args.start_year)

    try:
        if args.continuous:
            # Continuous mode for production
            logger.info("Starting continuous mode...")

            # Continuous loop - backfill from 2015 to current date
            while True:
                logger.info("Phase 1: Continuous backfill from 2015 to current date")

                # Check if we have completed backfill
                start_date = date(args.start_year, 1, 1)
                end_date = date.today() - timedelta(days=1)
                existing_dates = backfill.check_existing_dates()

                # Calculate total expected dates
                total_days = (end_date - start_date).days + 1

                if len(existing_dates) >= total_days * 0.95:  # Allow 5% gaps
                    logger.info(f"✅ Backfill complete! {len(existing_dates)} of {total_days} dates processed")
                    logger.info("Switching to maintenance mode...")
                else:
                    logger.info(f"Backfill progress: {len(existing_dates)} of {total_days} dates ({len(existing_dates)/total_days*100:.1f}%)")

                    # Run backfill for more dates
                    backfill.run_backfill(
                        resume=not args.no_resume,
                        max_days=args.max_days or 50  # Process 50 days at a time
                    )

                # Daily update cycle
                logger.info("\nPhase 2: Daily update and maintenance")

                # Wait until 1am UK time
                now = datetime.now()
                target_time = now.replace(hour=1, minute=0, second=0, microsecond=0)

                if now >= target_time:
                    # Already past 1am, wait until tomorrow
                    target_time += timedelta(days=1)

                wait_seconds = (target_time - now).total_seconds()

                # Only wait if we need to
                if wait_seconds > 0:
                    logger.info(f"Waiting {wait_seconds/3600:.1f} hours until next update at {target_time}")
                    time.sleep(wait_seconds)

                # Run daily update for recent dates
                backfill.run_daily_update()

                # Continue with next iteration
                logger.info("Continuing backfill and update cycle...")

        elif args.daily_update:
            # Just run daily update
            backfill.run_daily_update()
        else:
            # Run backfill
            backfill.run_backfill(
                resume=not args.no_resume,
                max_days=args.max_days
            )

    except KeyboardInterrupt:
        logger.info("\nBackfill interrupted by user")
    except Exception as e:
        logger.error(f"Backfill error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()