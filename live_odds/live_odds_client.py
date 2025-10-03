"""
Live Odds Supabase Client
Handles real-time updates to ra_odds_live table with efficient upserts
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from supabase import create_client, Client
import time

logger = logging.getLogger(__name__)


class LiveOddsSupabaseClient:
    """Client for managing live odds in Supabase"""

    def __init__(self):
        """Initialize Supabase client for live odds"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials in environment")

        # Initialize client with proper version handling
        try:
            # For supabase-py 2.x
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
        except Exception as e:
            # Log error and re-raise
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise ValueError(f"Could not initialize Supabase client: {e}")

        # Configuration
        self.batch_size = int(os.getenv('LIVE_BATCH_SIZE', '50'))
        self.max_retries = 3

        # Statistics
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'bookmakers': set(),
            'races': set(),
            'horses': set()
        }

        # Verify connection on startup
        self.verify_connection()

    def verify_connection(self):
        """Verify database connection works on startup"""
        try:
            logger.info(f"🔌 Connecting to Supabase at {self.supabase_url}")
            logger.info(f"   Table: ra_odds_live")
            response = self.client.table('ra_odds_live').select('id').limit(1).execute()
            logger.info("✅ Database connection verified successfully")
            logger.info(f"   Service key: {'configured' if self.supabase_key else 'NOT configured'}")
            return True
        except Exception as e:
            logger.error(f"❌ DATABASE CONNECTION FAILED: {e}")
            logger.error(f"   Supabase URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
            logger.error(f"   Service key configured: {'Yes' if os.getenv('SUPABASE_SERVICE_KEY') else 'No'}")
            raise RuntimeError(f"Cannot connect to Supabase database: {e}")

    def update_live_odds(self, odds_data: List[Dict]) -> Dict:
        """Update live odds with efficient batching and upserts"""
        logger.info(f"Updating {len(odds_data)} live odds records")
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'bookmakers': set(),
            'races': set(),
            'horses': set()
        }

        # Group by bookmaker for efficient updates
        bookmaker_groups = {}
        for record in odds_data:
            bookmaker_id = record.get('bookmaker_id')
            if bookmaker_id:
                if bookmaker_id not in bookmaker_groups:
                    bookmaker_groups[bookmaker_id] = []
                bookmaker_groups[bookmaker_id].append(record)

        # Process each bookmaker's odds
        for bookmaker_id, records in bookmaker_groups.items():
            logger.info(f"Processing {len(records)} records for {bookmaker_id}")
            self._process_bookmaker_batch(bookmaker_id, records)

        # Log statistics
        logger.info(f"Live odds update completed: {self.stats}")
        return self.stats

    def _process_bookmaker_batch(self, bookmaker_id: str, records: List[Dict]):
        """Process odds for a specific bookmaker"""
        # Process in batches
        for i in range(0, len(records), self.batch_size):
            batch = records[i:i+self.batch_size]

            try:
                prepared_records = []
                for record in batch:
                    prepared = self._prepare_live_record(record)
                    if prepared:
                        prepared_records.append(prepared)
                        # Track statistics
                        self.stats['bookmakers'].add(bookmaker_id)
                        self.stats['races'].add(record.get('race_id'))
                        self.stats['horses'].add(record.get('horse_id'))

                if prepared_records:
                    self._upsert_batch(prepared_records)

            except Exception as e:
                logger.error(f"Error processing batch for {bookmaker_id}: {e}")
                self.stats['errors'] += len(batch)

    def _prepare_live_record(self, record: Dict) -> Optional[Dict]:
        """Prepare a record for the ra_odds_live table"""
        try:
            # Convert datetime objects to ISO format strings
            odds_timestamp = record.get('odds_timestamp')
            if isinstance(odds_timestamp, datetime):
                odds_timestamp = odds_timestamp.isoformat()

            prepared = {
                # Identifiers
                'race_id': record.get('race_id'),
                'horse_id': record.get('horse_id'),
                'bookmaker_id': record.get('bookmaker_id'),

                # Race metadata
                'race_date': record.get('race_date'),
                'race_time': record.get('race_time'),
                'off_dt': record.get('off_dt'),
                'course': record.get('course'),
                'race_name': record.get('race_name'),
                'race_class': record.get('race_class'),
                'race_type': record.get('race_type'),
                'distance': record.get('distance'),
                'going': record.get('going'),
                'runners': record.get('runners'),

                # Horse metadata
                'horse_name': record.get('horse_name'),
                'horse_number': record.get('horse_number'),
                'jockey': record.get('jockey'),
                'trainer': record.get('trainer'),
                'draw': record.get('draw'),
                'weight': record.get('weight'),
                'age': record.get('age'),
                'form': record.get('form'),

                # Bookmaker information
                'bookmaker_name': record.get('bookmaker_name'),
                'bookmaker_type': record.get('bookmaker_type'),
                'market_type': 'WIN',  # Default to WIN market

                # Odds data
                'odds_decimal': record.get('odds_decimal'),
                'odds_fractional': record.get('odds_fractional'),
                'back_price': record.get('back_price'),
                'lay_price': record.get('lay_price'),
                'back_size': record.get('back_size'),
                'lay_size': record.get('lay_size'),

                # Market depth (JSON)
                'back_prices': json.dumps(record.get('back_prices')) if record.get('back_prices') else None,
                'lay_prices': json.dumps(record.get('lay_prices')) if record.get('lay_prices') else None,
                'total_matched': record.get('total_matched'),

                # Status
                'market_status': record.get('market_status', 'OPEN'),
                'in_play': record.get('in_play', False),

                # Timestamps
                'odds_timestamp': odds_timestamp,
                'updated_at': datetime.now().isoformat()
            }

            # Validate required fields
            if not all([prepared['race_id'], prepared['horse_id'], prepared['bookmaker_id']]):
                return None

            return prepared

        except Exception as e:
            logger.error(f"Error preparing live record: {e}")
            return None

    def _upsert_batch(self, records: List[Dict]):
        """Upsert a batch of records to ra_odds_live"""
        try:
            logger.info(f"💾 Upserting {len(records)} records to ra_odds_live...")

            # Log first record for debugging
            if records:
                sample = records[0]
                logger.info(f"   Sample record details:")
                logger.info(f"   - Horse: {sample.get('horse_name', 'unknown')}")
                logger.info(f"   - Course: {sample.get('course', 'unknown')}")
                logger.info(f"   - Bookmaker: {sample.get('bookmaker_name', 'unknown')} ({sample.get('bookmaker_id', 'unknown')})")
                logger.info(f"   - Race ID: {sample.get('race_id', 'unknown')}")
                logger.info(f"   - Horse ID: {sample.get('horse_id', 'unknown')}")
                logger.info(f"   - Odds: {sample.get('odds_decimal', 'N/A')}")
                logger.info(f"   - Timestamp: {sample.get('odds_timestamp', 'N/A')}")

            # Try upsert with conflict resolution
            logger.info(f"   🔄 Calling Supabase upsert...")
            response = self.client.table('ra_odds_live').upsert(
                records,
                on_conflict='race_id,horse_id,bookmaker_id'
            ).execute()
            logger.info(f"   ✅ Supabase upsert call completed")

            if response.data:
                count = len(response.data)
                self.stats['updated'] += count
                logger.info(f"✅ Successfully upserted {count} live odds records")
                logger.info(f"   Total in this session: {self.stats['updated']} records")
            else:
                logger.warning(f"⚠️  Upsert returned no data for {len(records)} records")

        except Exception as e:
            logger.error(f"❌ Upsert error to ra_odds_live: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")

            # Try without on_conflict if that's the issue
            try:
                logger.info("Retrying upsert without on_conflict parameter...")
                response = self.client.table('ra_odds_live').upsert(records).execute()
                if response.data:
                    count = len(response.data)
                    self.stats['updated'] += count
                    logger.info(f"✅ Retry successful: {count} records upserted")
                    return
            except Exception as retry_error:
                logger.error(f"Retry also failed: {retry_error}")

            self.stats['errors'] += len(records)
            raise

    def get_active_races(self) -> List[Dict]:
        """Get races that are currently active or upcoming"""
        try:
            # Get races in the next 4 hours
            future_time = (datetime.now() + timedelta(hours=4)).isoformat()

            response = self.client.table('ra_odds_live')\
                .select('race_id, course, race_name, off_dt')\
                .gte('off_dt', datetime.now().isoformat())\
                .lte('off_dt', future_time)\
                .execute()

            # Get unique races
            races = {}
            if response.data:
                for record in response.data:
                    race_id = record['race_id']
                    if race_id not in races:
                        races[race_id] = record

            return list(races.values())

        except Exception as e:
            logger.error(f"Error getting active races: {e}")
            return []

    def get_race_odds(self, race_id: str) -> List[Dict]:
        """Get all current odds for a specific race"""
        try:
            response = self.client.table('ra_odds_live')\
                .select('*')\
                .eq('race_id', race_id)\
                .order('horse_name,bookmaker_name')\
                .execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error getting race odds: {e}")
            return []

    def get_best_odds(self, race_id: str) -> List[Dict]:
        """Get best odds for each horse in a race"""
        try:
            # Get all odds for the race
            all_odds = self.get_race_odds(race_id)

            # Group by horse and find best odds
            horse_odds = {}
            for odds in all_odds:
                horse_id = odds['horse_id']
                if horse_id not in horse_odds:
                    horse_odds[horse_id] = {
                        'horse_id': horse_id,
                        'horse_name': odds['horse_name'],
                        'best_back': None,
                        'best_lay': None,
                        'best_fixed': None,
                        'bookmakers': []
                    }

                # Track best prices
                if odds['bookmaker_type'] == 'exchange':
                    if odds['back_price'] and (not horse_odds[horse_id]['best_back'] or
                                              odds['back_price'] > horse_odds[horse_id]['best_back']['price']):
                        horse_odds[horse_id]['best_back'] = {
                            'price': odds['back_price'],
                            'size': odds['back_size'],
                            'bookmaker': odds['bookmaker_name']
                        }

                    if odds['lay_price'] and (not horse_odds[horse_id]['best_lay'] or
                                             odds['lay_price'] < horse_odds[horse_id]['best_lay']['price']):
                        horse_odds[horse_id]['best_lay'] = {
                            'price': odds['lay_price'],
                            'size': odds['lay_size'],
                            'bookmaker': odds['bookmaker_name']
                        }
                else:
                    if odds['odds_decimal'] and (not horse_odds[horse_id]['best_fixed'] or
                                                odds['odds_decimal'] > horse_odds[horse_id]['best_fixed']['price']):
                        horse_odds[horse_id]['best_fixed'] = {
                            'price': odds['odds_decimal'],
                            'bookmaker': odds['bookmaker_name']
                        }

                horse_odds[horse_id]['bookmakers'].append(odds['bookmaker_name'])

            return list(horse_odds.values())

        except Exception as e:
            logger.error(f"Error getting best odds: {e}")
            return []

    def save_statistics(self, stats: Dict):
        """Save fetch statistics"""
        try:
            # Convert bookmakers list
            bookmakers_list = list(stats.get('bookmakers_found', []))

            record = {
                'fetch_timestamp': datetime.now().isoformat(),
                'race_id': stats.get('race_id'),  # Optional single race ID
                'races_count': len(stats.get('races', [])),
                'horses_count': len(stats.get('horses', [])),
                'bookmakers_found': len(bookmakers_list),
                'total_odds_fetched': stats.get('odds_fetched', 0),
                'bookmaker_list': bookmakers_list,  # Array of bookmaker names
                'fetch_duration_ms': stats.get('duration_seconds', 0) * 1000 if stats.get('duration_seconds') else None,
                'errors_count': stats.get('errors', 0)
            }

            response = self.client.table('ra_odds_statistics').insert(record).execute()
            logger.info("Live odds statistics saved")

        except Exception as e:
            logger.error(f"Failed to save statistics: {e}")

    def cleanup_old_odds(self, hours: int = 24):
        """Remove odds older than specified hours"""
        try:
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

            response = self.client.table('ra_odds_live')\
                .delete()\
                .lt('odds_timestamp', cutoff_time)\
                .execute()

            deleted = len(response.data) if response.data else 0
            logger.info(f"Cleaned up {deleted} old live odds records")
            return deleted

        except Exception as e:
            logger.error(f"Failed to cleanup old odds: {e}")
            return 0

    def get_bookmaker_coverage(self) -> Dict:
        """Get statistics on bookmaker coverage"""
        try:
            # Get count of odds per bookmaker for today's races
            today = datetime.now().date().isoformat()

            response = self.client.table('ra_odds_live')\
                .select('bookmaker_id, bookmaker_name')\
                .eq('race_date', today)\
                .execute()

            coverage = {}
            if response.data:
                for record in response.data:
                    bookmaker = record['bookmaker_name']
                    coverage[bookmaker] = coverage.get(bookmaker, 0) + 1

            return coverage

        except Exception as e:
            logger.error(f"Error getting bookmaker coverage: {e}")
            return {}

    def close(self):
        """Clean up resources"""
        pass