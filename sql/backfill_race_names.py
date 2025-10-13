#!/usr/bin/env python3
"""
Backfill race_name for existing ra_odds_historical records

This script:
1. Fetches all historical records missing race_name
2. Groups them by unique (date, track, race_time)
3. Queries Racing API results endpoint to get race_name
4. Updates all matching records with the race_name

This is more efficient than re-fetching all the data, as we only need
race metadata, not full runner details.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Set, Tuple
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from supabase import create_client, Client
import requests

# Load environment
env_file = Path(__file__).parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RaceNameBackfiller:
    """Backfill race names for existing historical records"""

    def __init__(self):
        """Initialize backfiller with Supabase and Racing API clients"""
        # Supabase setup
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Racing API setup
        self.username = os.getenv('RACING_API_USERNAME')
        self.password = os.getenv('RACING_API_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("RACING_API_USERNAME and RACING_API_PASSWORD required")

        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.base_url = "https://api.theracingapi.com/v1"

        # Stats
        self.stats = {
            'records_found': 0,
            'unique_races': 0,
            'api_calls': 0,
            'race_names_found': 0,
            'records_updated': 0,
            'errors': 0
        }

    def get_missing_race_name_records(self, limit: int = 10000) -> List[Dict]:
        """
        Get all records with NULL race_name

        Returns:
            List of records with date_of_race, track, race_time
        """
        logger.info("Fetching records with missing race_name...")

        try:
            response = self.supabase.table('ra_odds_historical')\
                .select('racing_bet_data_id, date_of_race, track, race_time')\
                .is_('race_name', 'null')\
                .order('date_of_race', desc=True)\
                .limit(limit)\
                .execute()

            records = response.data
            self.stats['records_found'] = len(records)
            logger.info(f"Found {len(records)} records missing race_name")

            return records

        except Exception as e:
            logger.error(f"Error fetching records: {e}")
            self.stats['errors'] += 1
            return []

    def group_by_race(self, records: List[Dict]) -> Dict[Tuple[str, str, str], List[int]]:
        """
        Group records by unique race (date, track, time)

        Returns:
            Dict mapping (date, track, time) -> list of record IDs
        """
        races = {}

        for record in records:
            date_str = record['date_of_race'].split('T')[0] if record.get('date_of_race') else None
            track = record.get('track')
            race_time = record.get('race_time')

            if not all([date_str, track, race_time]):
                continue

            race_key = (date_str, track, race_time)

            if race_key not in races:
                races[race_key] = []

            races[race_key].append(record['racing_bet_data_id'])

        self.stats['unique_races'] = len(races)
        logger.info(f"Grouped into {len(races)} unique races")

        return races

    def fetch_race_name_from_api(self, date: str, track: str, race_time: str) -> str:
        """
        Fetch race_name from Racing API results endpoint

        Args:
            date: Date in YYYY-MM-DD format
            track: Track name
            race_time: Race time (HH:MM:SS)

        Returns:
            race_name or None
        """
        try:
            url = f"{self.base_url}/results"
            params = {
                'start_date': date,
                'end_date': date,
                'region': ['gb', 'ire'],
                'limit': 50,
                'skip': 0
            }

            time.sleep(0.2)  # Rate limiting
            response = self.session.get(url, params=params, timeout=30)
            self.stats['api_calls'] += 1

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])

                # Find matching race
                for result in results:
                    result_track = result.get('course', '').upper()
                    result_time = result.get('off', '')  # Format: HH:MM or HH:MM:SS

                    # Match on track and time (allowing for time format differences)
                    if result_track == track.upper():
                        # Compare times (handle HH:MM vs HH:MM:SS)
                        if result_time and race_time:
                            result_time_short = result_time[:5]  # HH:MM
                            race_time_short = race_time[:5]  # HH:MM

                            if result_time_short == race_time_short:
                                race_name = result.get('race_name')
                                if race_name:
                                    logger.debug(f"Found race_name: {race_name}")
                                    return race_name

            elif response.status_code == 429:
                logger.warning("Rate limited, waiting 5 seconds...")
                time.sleep(5)
                return self.fetch_race_name_from_api(date, track, race_time)

            logger.debug(f"No race_name found for {track} at {race_time} on {date}")
            return None

        except Exception as e:
            logger.error(f"Error fetching race name from API: {e}")
            self.stats['errors'] += 1
            return None

    def update_records_with_race_name(self, record_ids: List[int], race_name: str) -> int:
        """
        Update multiple records with race_name

        Args:
            record_ids: List of racing_bet_data_id values
            race_name: Race name to set

        Returns:
            Number of records updated
        """
        try:
            # Batch update in groups of 100
            batch_size = 100
            total_updated = 0

            for i in range(0, len(record_ids), batch_size):
                batch = record_ids[i:i + batch_size]

                response = self.supabase.table('ra_odds_historical')\
                    .update({'race_name': race_name, 'updated_at': datetime.now().isoformat()})\
                    .in_('racing_bet_data_id', batch)\
                    .execute()

                if response.data:
                    batch_updated = len(response.data)
                    total_updated += batch_updated
                    logger.debug(f"Updated {batch_updated} records with race_name: {race_name}")

            return total_updated

        except Exception as e:
            logger.error(f"Error updating records: {e}")
            self.stats['errors'] += 1
            return 0

    def backfill_race_names(self, batch_size: int = 10000, max_races: int = None):
        """
        Main backfill process

        Args:
            batch_size: Number of records to fetch at once
            max_races: Maximum number of unique races to process (for testing)
        """
        logger.info("="*60)
        logger.info("RACE NAME BACKFILL STARTED")
        logger.info("="*60)

        # Step 1: Get records missing race_name
        records = self.get_missing_race_name_records(limit=batch_size)

        if not records:
            logger.info("No records need backfilling!")
            return

        # Step 2: Group by unique race
        races = self.group_by_race(records)

        if not races:
            logger.info("No valid races to process!")
            return

        # Step 3: Process each unique race
        race_count = 0
        for (date, track, race_time), record_ids in races.items():
            race_count += 1

            if max_races and race_count > max_races:
                logger.info(f"Reached max_races limit ({max_races}), stopping")
                break

            logger.info(f"Processing race {race_count}/{len(races)}: {track} on {date} at {race_time}")
            logger.info(f"  {len(record_ids)} records to update")

            # Fetch race_name from API
            race_name = self.fetch_race_name_from_api(date, track, race_time)

            if race_name:
                self.stats['race_names_found'] += 1

                # Update all records for this race
                updated = self.update_records_with_race_name(record_ids, race_name)
                self.stats['records_updated'] += updated
                logger.info(f"  ✅ Updated {updated} records with: {race_name}")
            else:
                logger.warning(f"  ⚠️  No race_name found in API")

            # Progress logging
            if race_count % 10 == 0:
                logger.info(f"Progress: {race_count}/{len(races)} races, {self.stats['records_updated']} records updated")

        # Final stats
        self.print_stats()

    def print_stats(self):
        """Print backfill statistics"""
        print("\n" + "="*60)
        print("BACKFILL STATISTICS")
        print("="*60)
        print(f"Records found missing race_name:  {self.stats['records_found']:,}")
        print(f"Unique races identified:           {self.stats['unique_races']:,}")
        print(f"API calls made:                    {self.stats['api_calls']:,}")
        print(f"Race names found in API:           {self.stats['race_names_found']:,}")
        print(f"Records updated:                   {self.stats['records_updated']:,}")
        print(f"Errors:                            {self.stats['errors']:,}")

        if self.stats['unique_races'] > 0:
            success_rate = (self.stats['race_names_found'] / self.stats['unique_races']) * 100
            print(f"Success rate:                      {success_rate:.1f}%")

        print("="*60 + "\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Backfill race names for historical odds')
    parser.add_argument('--batch-size', type=int, default=10000,
                       help='Number of records to fetch (default: 10000)')
    parser.add_argument('--max-races', type=int, default=None,
                       help='Maximum number of races to process (for testing)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without updating')

    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN MODE - No updates will be made")

    try:
        backfiller = RaceNameBackfiller()

        if args.dry_run:
            # Just fetch and show stats
            records = backfiller.get_missing_race_name_records(limit=args.batch_size)
            races = backfiller.group_by_race(records)
            backfiller.print_stats()
        else:
            # Run full backfill
            backfiller.backfill_race_names(
                batch_size=args.batch_size,
                max_races=args.max_races
            )

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
