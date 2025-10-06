#!/usr/bin/env python3
"""
Historical Data Backfill Script
Fetches racing data from 2015 to present for UK & Ireland
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import json
import time

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from config.config import get_config
from utils.logger import get_logger
from fetchers.results_fetcher import ResultsFetcher
from fetchers.races_fetcher import RacesFetcher

logger = get_logger('historical_backfill')


class HistoricalBackfill:
    """Backfill historical racing data from 2015 to present"""

    def __init__(self):
        self.config = get_config()
        self.results = {}
        self.start_time = None
        self.end_time = None

    def fetch_year_results(self, year: int) -> Dict:
        """
        Fetch race results for a specific year

        Args:
            year: Year to fetch (e.g., 2015)

        Returns:
            Results dictionary
        """
        logger.info("=" * 80)
        logger.info(f"FETCHING RESULTS FOR YEAR: {year}")
        logger.info("=" * 80)

        try:
            # Calculate days from start of year to end of year
            start_date = datetime(year, 1, 1)
            end_date = datetime(year, 12, 31)

            # If current year, only go up to today
            if year == datetime.now().year:
                end_date = datetime.now()

            days_in_period = (end_date - start_date).days + 1

            logger.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            logger.info(f"Days: {days_in_period}")

            # Fetch results
            fetcher = ResultsFetcher()
            result = fetcher.fetch_and_store(
                days_back=days_in_period,
                region_codes=['gb', 'ire'],
                start_date=start_date.strftime('%Y-%m-%d')
            )

            return result

        except Exception as e:
            logger.error(f"Error fetching year {year}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def fetch_year_races(self, year: int) -> Dict:
        """
        Fetch race cards for a specific year

        Args:
            year: Year to fetch (e.g., 2015)

        Returns:
            Results dictionary
        """
        logger.info("=" * 80)
        logger.info(f"FETCHING RACES FOR YEAR: {year}")
        logger.info("=" * 80)

        try:
            # Calculate days from start of year to end of year
            start_date = datetime(year, 1, 1)
            end_date = datetime(year, 12, 31)

            # If current year, only go up to today
            if year == datetime.now().year:
                end_date = datetime.now()

            days_in_period = (end_date - start_date).days + 1

            logger.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            logger.info(f"Days: {days_in_period}")

            # Fetch races
            fetcher = RacesFetcher()
            result = fetcher.fetch_and_store(
                days_back=days_in_period,
                region_codes=['gb', 'ire'],
                start_date=start_date.strftime('%Y-%m-%d')
            )

            return result

        except Exception as e:
            logger.error(f"Error fetching year {year}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def run_backfill(self, start_year: int = 2015, end_year: int = None,
                     entity: str = 'results', skip_years: List[int] = None) -> Dict:
        """
        Run historical backfill

        Args:
            start_year: Start year (default 2015)
            end_year: End year (default current year)
            entity: 'results' or 'races' or 'both'
            skip_years: List of years to skip (if already loaded)

        Returns:
            Complete results dictionary
        """
        self.start_time = datetime.utcnow()

        if end_year is None:
            end_year = datetime.now().year

        if skip_years is None:
            skip_years = []

        logger.info("=" * 80)
        logger.info("HISTORICAL DATA BACKFILL - UK & IRELAND RACING")
        logger.info(f"Period: {start_year} to {end_year}")
        logger.info(f"Entity: {entity}")
        logger.info(f"Started at: {self.start_time.isoformat()}")
        logger.info("=" * 80)

        years = range(start_year, end_year + 1)
        total_years = len(years)

        for idx, year in enumerate(years, 1):
            if year in skip_years:
                logger.info(f"[{idx}/{total_years}] Skipping year {year} (in skip list)")
                continue

            logger.info(f"\n[{idx}/{total_years}] Processing year {year}")
            logger.info("-" * 80)

            try:
                if entity in ['results', 'both']:
                    # Fetch results for this year
                    result = self.fetch_year_results(year)
                    self.results[f'results_{year}'] = {
                        'success': result.get('success', False),
                        'fetched': result.get('fetched', 0),
                        'inserted': result.get('inserted', 0),
                        'error': result.get('error'),
                        'timestamp': datetime.utcnow().isoformat()
                    }

                    if result.get('success'):
                        logger.info(f"✓ Results {year}: Fetched {result.get('fetched', 0)}, Inserted {result.get('inserted', 0)}")
                    else:
                        logger.error(f"✗ Results {year}: {result.get('error', 'Unknown error')}")

                    # Brief pause between years to respect API limits
                    time.sleep(2)

                if entity in ['races', 'both']:
                    # Fetch races for this year
                    result = self.fetch_year_races(year)
                    self.results[f'races_{year}'] = {
                        'success': result.get('success', False),
                        'fetched': result.get('fetched', 0),
                        'inserted': result.get('inserted', 0),
                        'error': result.get('error'),
                        'timestamp': datetime.utcnow().isoformat()
                    }

                    if result.get('success'):
                        logger.info(f"✓ Races {year}: Fetched {result.get('fetched', 0)}, Inserted {result.get('inserted', 0)}")
                    else:
                        logger.error(f"✗ Races {year}: {result.get('error', 'Unknown error')}")

                    # Brief pause between years
                    time.sleep(2)

            except Exception as e:
                logger.error(f"Exception processing year {year}: {e}", exc_info=True)
                self.results[f'error_{year}'] = {
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }

        self.end_time = datetime.utcnow()
        duration = (self.end_time - self.start_time).total_seconds()

        # Generate summary
        self._print_summary(duration, start_year, end_year)

        # Save results
        self._save_results()

        return self.results

    def _print_summary(self, duration: float, start_year: int, end_year: int):
        """Print execution summary"""
        logger.info("\n" + "=" * 80)
        logger.info("BACKFILL SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Period: {start_year} to {end_year}")
        logger.info(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes) ({duration/3600:.2f} hours)")
        logger.info(f"Start: {self.start_time.isoformat()}")
        logger.info(f"End: {self.end_time.isoformat()}")
        logger.info("\nResults by Year:")

        total_fetched = 0
        total_inserted = 0
        success_count = 0
        fail_count = 0

        for key, result in sorted(self.results.items()):
            status = "✓" if result.get('success') else "✗"
            fetched = result.get('fetched', 0)
            inserted = result.get('inserted', 0)

            logger.info(f"  [{status}] {key.ljust(20)} - Fetched: {fetched:8,}, Inserted: {inserted:8,}")

            total_fetched += fetched
            total_inserted += inserted
            if result.get('success'):
                success_count += 1
            else:
                fail_count += 1
                if result.get('error'):
                    logger.info(f"       Error: {result['error']}")

        logger.info(f"\nTotals:")
        logger.info(f"  Total Fetched: {total_fetched:,}")
        logger.info(f"  Total Inserted: {total_inserted:,}")
        logger.info(f"  Successful: {success_count}/{len(self.results)}")
        logger.info(f"  Failed: {fail_count}/{len(self.results)}")
        logger.info("=" * 80)

    def _save_results(self):
        """Save results to JSON file"""
        results_file = self.config.paths.logs_dir / f"backfill_results_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"

        results_summary = {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': (self.end_time - self.start_time).total_seconds(),
            'results': self.results
        }

        with open(results_file, 'w') as f:
            json.dump(results_summary, f, indent=2)

        logger.info(f"\nResults saved to: {results_file}")


def parse_args():
    """Parse command line arguments"""
    current_year = datetime.now().year

    parser = argparse.ArgumentParser(
        description='Historical Racing Data Backfill (2015-Present)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Backfill all results from 2015 to present
  python historical_backfill.py --entity results

  # Backfill specific years
  python historical_backfill.py --start 2020 --end 2023

  # Backfill both races and results
  python historical_backfill.py --entity both

  # Resume backfill, skip already completed years
  python historical_backfill.py --skip 2015 2016 2017
        '''
    )

    parser.add_argument(
        '--start',
        type=int,
        default=2015,
        help='Start year (default: 2015)'
    )

    parser.add_argument(
        '--end',
        type=int,
        default=current_year,
        help=f'End year (default: {current_year})'
    )

    parser.add_argument(
        '--entity',
        choices=['results', 'races', 'both'],
        default='results',
        help='Entity to backfill (default: results)'
    )

    parser.add_argument(
        '--skip',
        nargs='+',
        type=int,
        help='Years to skip (already completed)'
    )

    return parser.parse_args()


def main():
    """Main execution function"""
    args = parse_args()

    logger.info(f"Starting historical backfill: {args.start} to {args.end}")

    if args.skip:
        logger.info(f"Skipping years: {args.skip}")

    try:
        backfill = HistoricalBackfill()
        results = backfill.run_backfill(
            start_year=args.start,
            end_year=args.end,
            entity=args.entity,
            skip_years=args.skip
        )

        # Exit with appropriate code
        all_success = all(r.get('success', False) for r in results.values())
        sys.exit(0 if all_success else 1)

    except Exception as e:
        logger.error(f"FATAL ERROR: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
