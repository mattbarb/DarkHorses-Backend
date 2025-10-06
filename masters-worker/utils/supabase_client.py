"""
Supabase Database Client for Reference Data
Handles database operations with batching, upserts, and error handling
"""

import logging
from typing import Dict, List, Optional, Any
from supabase import create_client, Client
from datetime import datetime

logger = logging.getLogger(__name__)


class SupabaseReferenceClient:
    """Client for managing reference data in Supabase"""

    def __init__(self, url: str, service_key: str, batch_size: int = 100):
        """
        Initialize Supabase client

        Args:
            url: Supabase project URL
            service_key: Supabase service role key
            batch_size: Number of records per batch insert
        """
        self.url = url
        self.batch_size = batch_size

        try:
            self.client: Client = create_client(url, service_key)
            logger.info(f"Connected to Supabase at {url}")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise

        # Statistics
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }

    def verify_connection(self, table: str = 'ra_courses') -> bool:
        """Verify database connection"""
        try:
            result = self.client.table(table).select('*').limit(1).execute()
            logger.info(f"Database connection verified (test table: {table})")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def upsert_batch(self, table: str, records: List[Dict], unique_key: str = 'id') -> Dict:
        """
        Upsert batch of records

        Args:
            table: Table name
            records: List of record dictionaries
            unique_key: Column name for uniqueness check

        Returns:
            Statistics dictionary
        """
        if not records:
            logger.warning(f"No records to upsert for {table}")
            return {'inserted': 0, 'updated': 0, 'errors': 0}

        batch_stats = {'inserted': 0, 'updated': 0, 'errors': 0}

        # Process in batches
        for i in range(0, len(records), self.batch_size):
            batch = records[i:i + self.batch_size]

            try:
                # Upsert with on_conflict handling
                result = self.client.table(table).upsert(
                    batch,
                    on_conflict=unique_key
                ).execute()

                # Count as successful
                batch_stats['inserted'] += len(batch)
                logger.debug(f"Upserted {len(batch)} records to {table}")

            except Exception as e:
                batch_stats['errors'] += len(batch)
                logger.error(f"Error upserting batch to {table}: {e}")

        return batch_stats

    def insert_courses(self, courses: List[Dict]) -> Dict:
        """Insert/update courses"""
        logger.info(f"Inserting {len(courses)} courses")
        return self.upsert_batch('ra_courses', courses, 'course_id')

    def insert_horses(self, horses: List[Dict]) -> Dict:
        """Insert/update horses"""
        logger.info(f"Inserting {len(horses)} horses")
        return self.upsert_batch('ra_horses', horses, 'horse_id')

    def insert_jockeys(self, jockeys: List[Dict]) -> Dict:
        """Insert/update jockeys"""
        logger.info(f"Inserting {len(jockeys)} jockeys")
        return self.upsert_batch('ra_jockeys', jockeys, 'jockey_id')

    def insert_trainers(self, trainers: List[Dict]) -> Dict:
        """Insert/update trainers"""
        logger.info(f"Inserting {len(trainers)} trainers")
        return self.upsert_batch('ra_trainers', trainers, 'trainer_id')

    def insert_owners(self, owners: List[Dict]) -> Dict:
        """Insert/update owners"""
        logger.info(f"Inserting {len(owners)} owners")
        return self.upsert_batch('ra_owners', owners, 'owner_id')

    def insert_pedigree(self, pedigrees: List[Dict]) -> Dict:
        """Insert/update horse pedigree data"""
        logger.info(f"Inserting {len(pedigrees)} pedigree records")
        return self.upsert_batch('ra_horse_pedigree', pedigrees, 'horse_id')

    def insert_races(self, races: List[Dict]) -> Dict:
        """Insert/update races (unified table)"""
        logger.info(f"Inserting {len(races)} races")
        return self.upsert_batch('ra_races', races, 'race_id')

    def insert_runners(self, runners: List[Dict]) -> Dict:
        """Insert/update runners (unified table)"""
        logger.info(f"Inserting {len(runners)} runners")
        return self.upsert_batch('ra_runners', runners, 'runner_id')

    def insert_results(self, results: List[Dict]) -> Dict:
        """Insert/update results"""
        logger.info(f"Inserting {len(results)} results")
        return self.upsert_batch('ra_results', results, 'race_id')

    def insert_bookmakers(self, bookmakers: List[Dict]) -> Dict:
        """Insert/update bookmakers"""
        logger.info(f"Inserting {len(bookmakers)} bookmakers")
        return self.upsert_batch('ra_bookmakers', bookmakers, 'bookmaker_id')

    def get_existing_ids(self, table: str, id_column: str) -> set:
        """
        Get set of existing IDs from a table

        Args:
            table: Table name
            id_column: ID column name

        Returns:
            Set of existing IDs
        """
        try:
            result = self.client.table(table).select(id_column).execute()
            return {row[id_column] for row in result.data}
        except Exception as e:
            logger.error(f"Error getting existing IDs from {table}: {e}")
            return set()

    def get_table_count(self, table: str) -> int:
        """Get row count for a table"""
        try:
            result = self.client.table(table).select('*', count='exact').limit(1).execute()
            return result.count if hasattr(result, 'count') else 0
        except Exception as e:
            logger.error(f"Error getting count for {table}: {e}")
            return 0

    def get_stats(self) -> Dict:
        """Get client statistics"""
        return self.stats.copy()

    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
