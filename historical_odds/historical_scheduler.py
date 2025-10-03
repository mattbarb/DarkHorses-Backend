#!/usr/bin/env python3
"""
Historical Odds Scheduler
Schedules daily fetching of historical odds at 1am UK time
Includes automatic backfill for missing dates
"""

import os
import sys
import logging
import schedule
import time
import pytz
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
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

# Setup logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def fetch_yesterday_odds():
    """Daily job to fetch yesterday's odds"""
    logger.info("="*70)
    logger.info("SCHEDULED JOB: Fetching yesterday's odds")
    logger.info("="*70)

    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    try:
        # Initialize components
        fetcher = HistoricalOddsFetcher(rate_limit_delay=0.3)
        client = HistoricalOddsClient()

        logger.info(f"Fetching data for: {yesterday}")

        # Fetch odds
        odds_records = fetcher.fetch_date_odds(yesterday)

        if not odds_records:
            logger.warning(f"No odds found for {yesterday}")
            send_notification(
                subject=f"No odds data for {yesterday}",
                message=f"No odds records found for {yesterday}. This may be normal if no races occurred."
            )
            return

        logger.info(f"Fetched {len(odds_records)} odds records")

        # Store in database
        inserted = client.batch_insert_odds(odds_records)

        # Print statistics
        fetcher.print_stats()
        client.print_stats()

        logger.info(f"✓ Successfully processed {yesterday}")

        # Send success notification
        send_notification(
            subject=f"Historical odds fetched successfully - {yesterday}",
            message=f"""
Date: {yesterday}
Odds Records: {len(odds_records):,}
Inserted: {client.stats['inserted']:,}
Errors: {client.stats['errors']:,}

Data successfully stored in rb_odds_historical table.
            """
        )

    except Exception as e:
        logger.error(f"Error in scheduled job: {e}", exc_info=True)
        send_notification(
            subject=f"ERROR: Historical odds fetch failed - {yesterday}",
            message=f"Error fetching data for {yesterday}:\n\n{str(e)}"
        )


def check_and_backfill_missing():
    """Weekly job to check for and backfill missing dates"""
    logger.info("="*70)
    logger.info("SCHEDULED JOB: Checking for missing dates")
    logger.info("="*70)

    try:
        client = HistoricalOddsClient()

        # Check last 30 days for missing data
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        logger.info(f"Checking date range: {start_date} to {end_date}")

        missing_dates = client.get_missing_dates(start_date, end_date)

        if not missing_dates:
            logger.info("✓ No missing dates found")
            return

        logger.info(f"Found {len(missing_dates)} missing dates: {', '.join(missing_dates)}")

        # Send notification about missing dates
        send_notification(
            subject=f"Missing dates detected: {len(missing_dates)} dates",
            message=f"""
Date range checked: {start_date} to {end_date}
Missing dates: {len(missing_dates)}

Dates: {', '.join(missing_dates)}

Automatic backfill will attempt to fetch this data.
            """
        )

        # Backfill missing dates
        fetcher = HistoricalOddsFetcher(rate_limit_delay=0.3)
        success_count = 0

        for date in missing_dates:
            logger.info(f"Backfilling: {date}")

            try:
                odds_records = fetcher.fetch_date_odds(date)

                if odds_records:
                    inserted = client.batch_insert_odds(odds_records)
                    logger.info(f"✓ Backfilled {date}: {inserted} records")
                    success_count += 1
                else:
                    logger.warning(f"No data found for {date}")

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error backfilling {date}: {e}")

        # Send backfill completion notification
        send_notification(
            subject=f"Backfill complete: {success_count}/{len(missing_dates)} dates",
            message=f"""
Successfully backfilled: {success_count}/{len(missing_dates)} dates

Dates backfilled: {', '.join(missing_dates[:success_count])}
            """
        )

    except Exception as e:
        logger.error(f"Error in backfill job: {e}", exc_info=True)
        send_notification(
            subject="ERROR: Backfill job failed",
            message=f"Error during backfill operation:\n\n{str(e)}"
        )


def send_notification(subject: str, message: str):
    """
    Send notification email or log message

    Args:
        subject: Notification subject
        message: Notification message
    """
    # TODO: Implement email notifications if needed
    # For now, just log the notification
    logger.info(f"NOTIFICATION: {subject}")
    logger.info(message)


def main():
    """Main scheduler loop"""
    logger.info("="*70)
    logger.info("HISTORICAL ODDS SCHEDULER STARTED")
    logger.info("="*70)
    logger.info(f"Current time: {datetime.now()}")
    logger.info(f"Timezone: {pytz.timezone('Europe/London')}")

    # Schedule daily job at 1am UK time
    schedule.every().day.at("01:00").do(fetch_yesterday_odds)
    logger.info("✓ Scheduled: Daily fetch at 1:00 AM UK time")

    # Schedule weekly backfill check on Mondays at 2am
    schedule.every().monday.at("02:00").do(check_and_backfill_missing)
    logger.info("✓ Scheduled: Weekly backfill check on Mondays at 2:00 AM")

    # Always run on startup in cloud environments
    is_cloud = os.getenv('RENDER') or not Path('.env').exists()
    run_on_startup = is_cloud or os.getenv('RUN_ON_STARTUP', 'false').lower() == 'true'

    if run_on_startup or is_cloud:
        logger.info("🚀 Running immediate fetch on startup (cloud mode)")
        fetch_yesterday_odds()
    else:
        logger.info("Skipping startup fetch (RUN_ON_STARTUP=false)")

    logger.info("\nScheduler is running. Press Ctrl+C to stop.")
    logger.info("="*70 + "\n")

    # Main scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        logger.info("\nScheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()