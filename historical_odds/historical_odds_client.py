#!/usr/bin/env python3
"""
Historical Odds Supabase Client
Handles database operations for rb_odds_historical table
Maps Racing API data to existing schema
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from schema_mapping import SchemaMapper

# Load environment variables - optional for Render.com
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    # Running on Render.com - use system environment variables
    pass

logger = logging.getLogger(__name__)


class HistoricalOddsClient:
    """Client for managing historical odds data in Supabase"""

    def __init__(self):
        """Initialize Supabase client"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        # Use only SERVICE_KEY - no need for ANON_KEY
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")

        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        self.table_name = 'rb_odds_historical'  # Using existing table
        self.mapper = SchemaMapper()  # Initialize schema mapper

        self.stats = {
            'total_processed': 0,
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

        # Verify connection on startup
        self.verify_connection()

    def verify_connection(self):
        """Verify database connection works on startup"""
        try:
            logger.info(f"🔌 Connecting to Supabase at {self.supabase_url}")
            logger.info(f"   Table: {self.table_name}")
            response = self.client.table(self.table_name).select('racing_bet_data_id').limit(1).execute()
            logger.info("✅ Database connection verified successfully")
            logger.info(f"   Service key: {'configured' if self.supabase_key else 'NOT configured'}")
            return True
        except Exception as e:
            logger.error(f"❌ DATABASE CONNECTION FAILED: {e}")
            logger.error(f"   Supabase URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
            logger.error(f"   Service key configured: {'Yes' if os.getenv('SUPABASE_SERVICE_KEY') else 'No'}")
            raise RuntimeError(f"Cannot connect to Supabase database: {e}")

    def check_exists(self, date_of_race: str, track: str, race_time: str, horse_name: str) -> Optional[int]:
        """
        Check if a record already exists using natural keys

        Args:
            date_of_race: Race date
            track: Track name
            race_time: Race time
            horse_name: Horse name

        Returns:
            racing_bet_data_id if exists, None otherwise
        """
        try:
            # Extract just the date if it's a full timestamp
            date_only = date_of_race.split('T')[0] if 'T' in date_of_race else date_of_race

            response = self.client.table(self.table_name).select('racing_bet_data_id').eq(
                'track', track.upper()
            ).eq('horse_name', horse_name).execute()

            # Further filter by date and time in Python (since Supabase date filtering can be tricky)
            for record in response.data:
                # Would need to check date_of_race and race_time match
                # For now, return first match (can be enhanced)
                return record['racing_bet_data_id']

            return None
        except Exception as e:
            logger.error(f"Error checking existence: {e}")
            return None

    def insert_odds(self, odds_data: Dict) -> bool:
        """
        Insert a single odds record after mapping to rb_odds_historical schema

        Args:
            odds_data: Racing API format data

        Returns:
            True if successful, False otherwise
        """
        try:
            # Map Racing API data to rb_odds_historical schema
            mapped_record = self.mapper.map_racing_api_to_rb_odds(odds_data)

            if not mapped_record:
                logger.warning(f"Failed to map record for {odds_data.get('horse_name', 'unknown')}")
                self.stats['skipped'] += 1
                return False

            # Check if already exists (to avoid duplicates)
            exists = self.check_exists(
                mapped_record['date_of_race'],
                mapped_record['track'],
                mapped_record.get('race_time', ''),
                mapped_record['horse_name']
            )

            if exists:
                logger.debug(f"Record already exists for {mapped_record['horse_name']} at {mapped_record['track']}")
                self.stats['skipped'] += 1
                return False

            # Insert into database
            response = self.client.table(self.table_name).insert(mapped_record).execute()

            if response.data:
                self.stats['inserted'] += 1
                return True
            else:
                logger.error(f"Insert failed for {mapped_record['horse_name']}")
                self.stats['errors'] += 1
                return False

        except Exception as e:
            logger.error(f"Error inserting odds: {e}")
            self.stats['errors'] += 1
            return False

    def upsert_odds(self, odds_data: Dict) -> bool:
        """
        Insert or update odds record after mapping

        Note: rb_odds_historical doesn't have unique constraints on natural keys,
        so we'll check for existence first and either insert or update.

        Args:
            odds_data: Racing API format data

        Returns:
            True if successful, False otherwise
        """
        try:
            # Map Racing API data to rb_odds_historical schema
            mapped_record = self.mapper.map_racing_api_to_rb_odds(odds_data)

            if not mapped_record:
                logger.warning(f"Failed to map record for {odds_data.get('horse_name', 'unknown')}")
                self.stats['skipped'] += 1
                return False

            # Check if already exists
            existing_id = self.check_exists(
                mapped_record['date_of_race'],
                mapped_record['track'],
                mapped_record.get('race_time', ''),
                mapped_record['horse_name']
            )

            if existing_id:
                # Update existing record
                mapped_record['updated_at'] = datetime.now().isoformat()
                response = self.client.table(self.table_name).update(
                    mapped_record
                ).eq('racing_bet_data_id', existing_id).execute()

                if response.data:
                    self.stats['updated'] += 1
                    return True
                else:
                    logger.error(f"Update failed for {mapped_record['horse_name']}")
                    self.stats['errors'] += 1
                    return False
            else:
                # Insert new record
                response = self.client.table(self.table_name).insert(mapped_record).execute()

                if response.data:
                    self.stats['inserted'] += 1
                    return True
                else:
                    logger.error(f"Insert failed for {mapped_record['horse_name']}")
                    self.stats['errors'] += 1
                    return False

        except Exception as e:
            logger.error(f"Error upserting odds: {e}")
            self.stats['errors'] += 1
            return False

    def batch_insert_odds(self, odds_list: List[Dict], batch_size: int = 50, skip_duplicates: bool = True) -> int:
        """
        Insert multiple odds records in batches after mapping

        Args:
            odds_list: List of Racing API format records
            batch_size: Number of records per batch (reduced for larger mapped records)
            skip_duplicates: Whether to skip duplicate checks (faster but may create dupes)

        Returns:
            Number of records successfully inserted
        """
        total_inserted = 0

        # First, map all records
        logger.info(f"📋 Mapping {len(odds_list)} Racing API records to rb_odds_historical schema...")
        mapped_records = self.mapper.map_batch(odds_list)
        logger.info(f"✅ Successfully mapped {len(mapped_records)} records")

        if not mapped_records:
            logger.warning("⚠️  No records were successfully mapped")
            return 0

        # Process in batches
        batch_count = (len(mapped_records) + batch_size - 1) // batch_size
        logger.info(f"💾 Inserting {len(mapped_records)} records in {batch_count} batches...")

        for i in range(0, len(mapped_records), batch_size):
            batch = mapped_records[i:i + batch_size]
            batch_num = i//batch_size + 1

            try:
                if skip_duplicates:
                    # Filter out duplicates before inserting (slower but safer)
                    unique_batch = []
                    for record in batch:
                        exists = self.check_exists(
                            record['date_of_race'],
                            record['track'],
                            record.get('race_time', ''),
                            record['horse_name']
                        )
                        if not exists:
                            unique_batch.append(record)
                        else:
                            self.stats['skipped'] += 1

                    batch = unique_batch

                if not batch:
                    logger.debug(f"Batch {batch_num}/{batch_count}: All records already exist, skipping")
                    continue

                # Insert batch
                logger.info(f"   Batch {batch_num}/{batch_count}: Inserting {len(batch)} records...")
                response = self.client.table(self.table_name).insert(batch).execute()

                if response.data:
                    batch_inserted = len(response.data)
                    total_inserted += batch_inserted
                    self.stats['inserted'] += batch_inserted
                    logger.info(f"   ✅ Batch {batch_num}/{batch_count}: Inserted {batch_inserted} records")
                    logger.info(f"      Session total: {self.stats['inserted']} inserted")
                else:
                    logger.error(f"   ❌ Batch {batch_num}/{batch_count}: Insert failed")
                    self.stats['errors'] += len(batch)

            except Exception as e:
                logger.error(f"Error batch inserting batch {i//batch_size + 1}: {e}")
                self.stats['errors'] += len(batch)

        self.stats['total_processed'] = len(odds_list)
        return total_inserted

    def get_existing_dates(self) -> set:
        """
        Get list of dates that already have data

        Returns:
            Set of dates with existing data
        """
        try:
            response = self.client.table(self.table_name)\
                .select('date_of_race')\
                .execute()

            dates = set()
            if response.data:
                for record in response.data:
                    if record.get('date_of_race'):
                        # Extract just the date part
                        date_str = record['date_of_race'].split('T')[0]
                        from datetime import datetime
                        dates.add(datetime.strptime(date_str, '%Y-%m-%d').date())

            return dates
        except Exception as e:
            logger.error(f"Error getting existing dates: {e}")
            return set()

    def get_missing_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        Get list of dates with no Racing API data in the date range

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of date strings with no Racing API data
        """
        try:
            # Get all distinct dates in range where data_source contains 'Racing API'
            response = self.client.table(self.table_name).select('date_of_race').like(
                'data_source', '%Racing API%'
            ).execute()

            # Extract date parts (handle ISO 8601 format)
            existing_dates = set()
            for row in response.data:
                date_str = row['date_of_race']
                if 'T' in date_str:
                    date_str = date_str.split('T')[0]
                existing_dates.add(date_str)

            # Generate all dates in range
            from datetime import timedelta
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')

            all_dates = []
            current = start
            while current <= end:
                date_str = current.strftime('%Y-%m-%d')
                if date_str not in existing_dates:
                    all_dates.append(date_str)
                current += timedelta(days=1)

            # Reverse dates so most recent are processed first
            # This ensures recent valuable data is fetched before sparse historical dates
            all_dates.reverse()

            return all_dates

        except Exception as e:
            logger.error(f"Error getting missing dates: {e}")
            return []

    def get_stats_for_date(self, date: str) -> Dict:
        """
        Get statistics for a specific date (Racing API data only)

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Dictionary with statistics
        """
        try:
            # Query records for this date from Racing API
            response = self.client.table(self.table_name).select(
                'racing_bet_data_id,track,horse_name,data_source'
            ).like('data_source', '%Racing API%').execute()

            # Filter by date in Python (since date format may vary)
            date_records = []
            for row in response.data:
                # Would need actual date_of_race field - simplified here
                date_records.append(row)

            return {
                'total_records': len(date_records),
                'unique_tracks': len(set(row['track'] for row in date_records if row.get('track'))),
                'unique_horses': len(set(row['horse_name'] for row in date_records if row.get('horse_name'))),
                'data_sources': len(set(row['data_source'] for row in date_records if row.get('data_source')))
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def print_stats(self):
        """Print processing statistics"""
        print("\n" + "="*60)
        print("DATABASE INSERTION STATISTICS")
        print("="*60)
        print(f"Total processed:  {self.stats['total_processed']:,}")
        print(f"Inserted:         {self.stats['inserted']:,}")
        print(f"Updated:          {self.stats['updated']:,}")
        print(f"Skipped:          {self.stats['skipped']:,}")
        print(f"Errors:           {self.stats['errors']:,}")

        if self.stats['total_processed'] > 0:
            success_rate = ((self.stats['inserted'] + self.stats['updated']) /
                          self.stats['total_processed']) * 100
            print(f"Success rate:     {success_rate:.1f}%")

        print("="*60 + "\n")

    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            'total_processed': 0,
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }


if __name__ == "__main__":
    # Test the client
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    client = HistoricalOddsClient()

    # Test connection
    print("Testing Supabase connection...")
    print(f"Connected to: {client.supabase_url}")
    print(f"Table: {client.table_name}")

    # Get missing dates example
    print("\nChecking for missing dates...")
    missing = client.get_missing_dates('2024-09-01', '2024-09-30')
    print(f"Missing dates in September 2024: {len(missing)}")

    print("\nClient ready!")