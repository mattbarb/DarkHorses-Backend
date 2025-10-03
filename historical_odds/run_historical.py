#!/usr/bin/env python3
"""
Historical Odds Runner
Main entry point for fetching and storing historical odds data
Designed to run daily at 1am UK time to capture previous day's races
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from historical_odds_fetcher import HistoricalOddsFetcher
from historical_odds_client import HistoricalOddsClient

# Load environment variables - optional for Render.com
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    # Running on Render.com - use system environment variables
    pass

# Setup logging - stdout only for Render.com
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Only stdout for Render.com
    ]
)

logger = logging.getLogger(__name__)


def fetch_and_store_date(date: str, fetcher: HistoricalOddsFetcher,
                         client: HistoricalOddsClient, dry_run: bool = False) -> bool:
    """
    Fetch and store odds for a specific date

    Args:
        date: Date in YYYY-MM-DD format
        fetcher: Historical odds fetcher instance
        client: Database client instance
        dry_run: If True, fetch but don't store

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Processing date: {date}")

        # Fetch odds for the date (limit races in dry run mode for testing)
        if dry_run:
            odds_records = fetcher.fetch_date_odds(date, limit_for_test=2)  # Only test 2 races
        else:
            odds_records = fetcher.fetch_date_odds(date)

        if not odds_records:
            logger.warning(f"No odds found for {date}")
            return True  # Not an error, just no data

        logger.info(f"Fetched {len(odds_records)} odds records for {date}")

        if dry_run:
            logger.info("[DRY RUN] Skipping database insertion")
            # Show sample record
            if odds_records:
                print("\nSample record:")
                for key, value in list(odds_records[0].items())[:10]:
                    print(f"  {key}: {value}")
            return True

        # Store in database
        logger.info(f"Inserting {len(odds_records)} records into database...")
        inserted = client.batch_insert_odds(odds_records)

        logger.info(f"Successfully inserted {inserted} records for {date}")
        return True

    except Exception as e:
        logger.error(f"Error processing date {date}: {e}", exc_info=True)
        return False


def run_yesterday():
    """Fetch and store yesterday's data (default daily operation)"""
    logger.info("="*70)
    logger.info("HISTORICAL ODDS FETCHER - YESTERDAY MODE")
    logger.info("="*70)

    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    logger.info(f"Fetching data for: {yesterday}")

    # Initialize components
    fetcher = HistoricalOddsFetcher(rate_limit_delay=0.3)
    client = HistoricalOddsClient()

    # Process yesterday
    success = fetch_and_store_date(yesterday, fetcher, client)

    # Print statistics
    fetcher.print_stats()
    client.print_stats()

    if success:
        logger.info("✓ Yesterday's data successfully fetched and stored")
        return 0
    else:
        logger.error("✗ Failed to fetch yesterday's data")
        return 1


def run_date_range(start_date: str, end_date: str, dry_run: bool = False):
    """Fetch and store data for a date range (backfill operation)"""
    logger.info("="*70)
    logger.info(f"HISTORICAL ODDS FETCHER - DATE RANGE MODE {'[DRY RUN]' if dry_run else ''}")
    logger.info("="*70)

    logger.info(f"Date range: {start_date} to {end_date}")

    # Initialize components
    fetcher = HistoricalOddsFetcher(rate_limit_delay=0.3)
    client = HistoricalOddsClient()

    # Generate date list
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    logger.info(f"Processing {len(dates)} dates...")

    # Process each date
    success_count = 0
    for i, date in enumerate(dates, 1):
        logger.info(f"\nDate {i}/{len(dates)}: {date}")

        if fetch_and_store_date(date, fetcher, client, dry_run):
            success_count += 1
        else:
            logger.error(f"Failed to process {date}")

        # Brief pause between dates
        if i < len(dates):
            import time
            time.sleep(1)

    # Print final statistics
    fetcher.print_stats()
    if not dry_run:
        client.print_stats()

    logger.info(f"\nProcessed {success_count}/{len(dates)} dates successfully")

    if success_count == len(dates):
        logger.info("✓ All dates successfully processed")
        return 0
    else:
        logger.warning(f"✗ Some dates failed ({len(dates) - success_count} failures)")
        return 1


def run_backfill_missing():
    """Find and backfill missing dates in database"""
    logger.info("="*70)
    logger.info("HISTORICAL ODDS FETCHER - BACKFILL MISSING DATES")
    logger.info("="*70)

    # Initialize client
    client = HistoricalOddsClient()

    # Define date range (e.g., last 90 days)
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

    logger.info(f"Checking for missing dates between {start_date} and {end_date}")

    # Get missing dates
    missing_dates = client.get_missing_dates(start_date, end_date)

    if not missing_dates:
        logger.info("✓ No missing dates found")
        return 0

    logger.info(f"Found {len(missing_dates)} missing dates")
    logger.info(f"Missing dates: {', '.join(missing_dates[:10])}" +
               (f" ... and {len(missing_dates) - 10} more" if len(missing_dates) > 10 else ""))

    # Ask for confirmation
    response = input(f"\nBackfill {len(missing_dates)} missing dates? (y/n): ")
    if response.lower() != 'y':
        logger.info("Backfill cancelled")
        return 0

    # Initialize fetcher
    fetcher = HistoricalOddsFetcher(rate_limit_delay=0.3)

    # Process missing dates
    success_count = 0
    for i, date in enumerate(missing_dates, 1):
        logger.info(f"\nBackfilling {i}/{len(missing_dates)}: {date}")

        if fetch_and_store_date(date, fetcher, client):
            success_count += 1
        else:
            logger.error(f"Failed to backfill {date}")

        # Brief pause between dates
        if i < len(missing_dates):
            import time
            time.sleep(1)

    # Print statistics
    fetcher.print_stats()
    client.print_stats()

    logger.info(f"\nBackfilled {success_count}/{len(missing_dates)} dates successfully")

    if success_count == len(missing_dates):
        logger.info("✓ All missing dates successfully backfilled")
        return 0
    else:
        logger.warning(f"✗ Some dates failed ({len(missing_dates) - success_count} failures)")
        return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Historical Odds Fetcher - Fetch and store completed race odds',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch yesterday's data (default daily operation)
  python3 run_historical.py

  # Fetch specific date
  python3 run_historical.py --date 2024-09-29

  # Fetch date range (backfill)
  python3 run_historical.py --start 2024-09-01 --end 2024-09-30

  # Test mode (fetch but don't store)
  python3 run_historical.py --date 2024-09-29 --dry-run

  # Find and backfill missing dates
  python3 run_historical.py --backfill-missing

Designed for:
  - Daily automated runs at 1am UK time (fetches previous day)
  - Manual backfill operations for historical data
  - Gap detection and automatic backfilling
        """
    )

    parser.add_argument('--date', type=str,
                       help='Specific date to fetch (YYYY-MM-DD)')
    parser.add_argument('--start', type=str,
                       help='Start date for range (YYYY-MM-DD)')
    parser.add_argument('--end', type=str,
                       help='End date for range (YYYY-MM-DD)')
    parser.add_argument('--backfill-missing', action='store_true',
                       help='Find and backfill missing dates')
    parser.add_argument('--dry-run', action='store_true',
                       help='Fetch data but do not store in database')
    parser.add_argument('--yesterday', action='store_true',
                       help='Explicitly fetch yesterday (default)')

    args = parser.parse_args()

    try:
        # Backfill missing dates
        if args.backfill_missing:
            return run_backfill_missing()

        # Date range mode
        if args.start and args.end:
            return run_date_range(args.start, args.end, args.dry_run)

        # Single date mode
        if args.date:
            fetcher = HistoricalOddsFetcher(rate_limit_delay=0.3)
            client = HistoricalOddsClient()

            logger.info(f"{'[DRY RUN] ' if args.dry_run else ''}Fetching data for: {args.date}")

            success = fetch_and_store_date(args.date, fetcher, client, args.dry_run)

            fetcher.print_stats()
            if not args.dry_run:
                client.print_stats()

            return 0 if success else 1

        # Default: yesterday mode
        return run_yesterday()

    except KeyboardInterrupt:
        logger.warning("\nOperation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())