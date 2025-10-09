"""
Live Odds Supabase Client
Handles real-time updates to ra_odds_live table with efficient upserts
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from supabase import create_client, Client
import time

# Add parent directory to path for redis_cache import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

logger = logging.getLogger(__name__)

# Import Redis cache for invalidation (optional - won't break if not available)
try:
    from redis_cache import invalidate_races_cache
    CACHE_INVALIDATION_AVAILABLE = True
except ImportError:
    logger.debug("Redis cache invalidation not available")
    CACHE_INVALIDATION_AVAILABLE = False
    def invalidate_races_cache():
        return False


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
        # Reduced batch size for faster writes and less table locking
        # Smaller batches = shorter locks = frontend can read between batches
        self.batch_size = int(os.getenv('LIVE_BATCH_SIZE', '100'))  # Reduced from larger batches
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

    def fetch_existing_odds_for_races(self, race_ids: List[str]) -> Dict[tuple, float]:
        """
        Fetch existing odds for given races to enable change detection.

        Args:
            race_ids: List of race IDs to fetch existing odds for

        Returns:
            Dict mapping (race_id, horse_id, bookmaker_id) -> odds_decimal
        """
        try:
            if not race_ids:
                logger.info("📭 No race IDs provided - assuming all new records")
                return {}

            # SAFEGUARD: Prevent accidentally fetching too many races
            # This caused frontend hangs when fetching 50-100+ races (82k+ rows, 5-15s)
            if len(race_ids) > 20:
                logger.warning(f"⚠️  WARNING: Fetching {len(race_ids)} races - this may be too many!")
                logger.warning(f"   Expected: 2-5 races per cycle")
                logger.warning(f"   This could cause slow queries (5-15s) and block frontend")
                logger.warning(f"   Consider limiting to races actually being updated")

            logger.info(f"📥 Fetching existing odds for {len(race_ids)} races (change detection)...")

            # Query Supabase for all odds in these races
            response = self.client.table('ra_odds_live') \
                .select('race_id,horse_id,bookmaker_id,odds_decimal') \
                .in_('race_id', race_ids) \
                .execute()

            if not response.data:
                logger.info("📭 No existing odds found (all records are new)")
                return {}

            # Build lookup map
            odds_map = {}
            for row in response.data:
                key = (row['race_id'], row['horse_id'], row['bookmaker_id'])
                odds_map[key] = row['odds_decimal']

            logger.info(f"✅ Loaded {len(odds_map)} existing odds records for comparison")
            return odds_map

        except Exception as e:
            logger.error(f"❌ Error fetching existing odds: {e}")
            # Return empty map - fall back to upserting all (safe default)
            return {}

    def update_live_odds(self, odds_data: List[Dict], race_ids: List[str] = None) -> Dict:
        """
        Update live odds with change detection - ONLY writes when odds actually change.

        Args:
            odds_data: List of odds records to update
            race_ids: Optional list of race IDs for bulk existing odds fetch

        Returns:
            Dict with upsert statistics including 'skipped' count
        """
        logger.info(f"📥 RECEIVED {len(odds_data)} odds records to update")

        # EMERGENCY BYPASS: Disable change detection if causing database locks
        disable_change_detection = os.getenv('DISABLE_CHANGE_DETECTION', 'false').lower() == 'true'
        if disable_change_detection:
            logger.warning("⚠️ CHANGE DETECTION DISABLED - Upserting all records")
            try:
                response = self.client.table('ra_odds_live').upsert(
                    odds_data,
                    on_conflict='race_id,horse_id,bookmaker_id'
                ).execute()
                logger.info(f"✅ Upserted {len(odds_data)} records (change detection disabled)")
                return {
                    "inserted": 0,
                    "updated": len(odds_data),
                    "skipped": 0
                }
            except Exception as e:
                logger.error(f"❌ Error upserting odds: {e}")
                raise

        # Log sample of first record
        if odds_data:
            sample = odds_data[0]
            logger.info(f"   Sample record keys: {list(sample.keys())[:10]}...")
            logger.info(f"   Sample race_id: {sample.get('race_id')}")
            logger.info(f"   Sample horse_id: {sample.get('horse_id')}")
            logger.info(f"   Sample bookmaker_id: {sample.get('bookmaker_id')}")

        self.stats = {
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'bookmakers': set(),
            'races': set(),
            'horses': set()
        }

        # STEP 1: Fetch existing odds for change detection
        if race_ids is None:
            # Extract race IDs from odds data
            race_ids = list(set(record.get('race_id') for record in odds_data if record.get('race_id')))
            logger.info(f"   Extracted {len(race_ids)} unique race IDs from odds data")

        existing_odds_map = self.fetch_existing_odds_for_races(race_ids)

        # STEP 2: Filter to only changed/new odds
        odds_to_upsert = []
        skipped_count = 0

        for record in odds_data:
            race_id = record.get('race_id')
            horse_id = record.get('horse_id')
            bookmaker_id = record.get('bookmaker_id')
            new_odds_decimal = record.get('odds_decimal')

            if not race_id or not horse_id or not bookmaker_id:
                logger.warning(f"⚠️  Record missing required ID fields: {record.get('horse_name', 'unknown')}")
                continue

            key = (race_id, horse_id, bookmaker_id)
            existing_decimal = existing_odds_map.get(key)

            # Check if odds changed (or is a new record)
            if existing_decimal is not None:
                # Record exists - compare odds
                try:
                    # Convert to float for comparison (handle None)
                    existing_float = float(existing_decimal) if existing_decimal is not None else None
                    new_float = float(new_odds_decimal) if new_odds_decimal is not None else None

                    if existing_float == new_float:
                        # Odds unchanged - skip
                        skipped_count += 1
                        continue
                except (ValueError, TypeError):
                    # If conversion fails, assume changed and upsert
                    pass

            # Odds changed or new record - add to upsert batch
            odds_to_upsert.append(record)

        # Update stats with skipped count
        self.stats['skipped'] = skipped_count

        logger.info(f"📊 Change detection: {len(odds_to_upsert)} to update/insert, {skipped_count} unchanged (skipped)")

        # STEP 3: Only proceed if there are changes
        if not odds_to_upsert:
            logger.info("✅ No odds changes detected - skipping database write (reduces cost)")
            return {
                'inserted': 0,
                'updated': 0,
                'skipped': skipped_count,
                'errors': 0,
                'bookmakers': 0,
                'races': 0,
                'horses': 0
            }

        # STEP 4: Process only changed odds (original logic)
        # Group by bookmaker for efficient updates
        bookmaker_groups = {}
        for record in odds_to_upsert:
            bookmaker_id = record.get('bookmaker_id')
            if bookmaker_id:
                if bookmaker_id not in bookmaker_groups:
                    bookmaker_groups[bookmaker_id] = []
                bookmaker_groups[bookmaker_id].append(record)
            else:
                logger.warning(f"⚠️  Record missing bookmaker_id: {record.get('horse_name', 'unknown')}")

        logger.info(f"📦 Grouped {len(odds_to_upsert)} changed records into {len(bookmaker_groups)} bookmakers: {list(bookmaker_groups.keys())}")

        # Process each bookmaker's odds
        for bookmaker_id, records in bookmaker_groups.items():
            logger.debug(f"Processing {len(records)} records for bookmaker: {bookmaker_id}")
            self._process_bookmaker_batch(bookmaker_id, records, existing_odds_map)

        # Log compact summary with skipped count
        logger.info(f"✅ Cycle complete: {self.stats['updated']} updated | {self.stats['skipped']} skipped | {len(self.stats['races'])} races | {len(self.stats['horses'])} horses | {len(self.stats['bookmakers'])} bookmakers | {self.stats['errors']} errors")

        # Invalidate API cache if we actually updated records
        if self.stats['updated'] > 0 and CACHE_INVALIDATION_AVAILABLE:
            invalidate_races_cache()

        # Return stats with counts including skipped
        return {
            'inserted': self.stats['inserted'],
            'updated': self.stats['updated'],
            'skipped': self.stats['skipped'],
            'errors': self.stats['errors'],
            'bookmakers': len(self.stats['bookmakers']),
            'races': len(self.stats['races']),
            'horses': len(self.stats['horses'])
        }

    def _process_bookmaker_batch(self, bookmaker_id: str, records: List[Dict], existing_odds_map: Dict[tuple, float] = None):
        """
        Process odds for a specific bookmaker

        Args:
            bookmaker_id: ID of the bookmaker
            records: List of odds records for this bookmaker
            existing_odds_map: Optional map of existing odds (for determining insert vs update)
        """
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

                        # Track if this is an insert or update
                        if existing_odds_map is not None:
                            key = (record.get('race_id'), record.get('horse_id'), bookmaker_id)
                            if key in existing_odds_map:
                                self.stats['updated'] += 1
                            else:
                                self.stats['inserted'] += 1

                if prepared_records:
                    self._upsert_batch(prepared_records, count_in_stats=False)  # Don't double-count

            except Exception as e:
                logger.error(f"Error processing batch for {bookmaker_id}: {e}")
                self.stats['errors'] += len(batch)

    def _sanitize_value(self, value, expected_type='str'):
        """Sanitize a value for database insertion - convert empty strings to None"""
        if value == '' or value is None:
            return None
        if expected_type == 'int':
            try:
                return int(value) if value else None
            except (ValueError, TypeError):
                return None
        if expected_type == 'float':
            try:
                return float(value) if value else None
            except (ValueError, TypeError):
                return None
        return value

    def _prepare_live_record(self, record: Dict) -> Optional[Dict]:
        """Prepare a record for the ra_odds_live table"""
        try:
            # Convert datetime objects to ISO format strings
            odds_timestamp = record.get('odds_timestamp')
            if isinstance(odds_timestamp, datetime):
                odds_timestamp = odds_timestamp.isoformat()

            prepared = {
                # Identifiers
                'race_id': self._sanitize_value(record.get('race_id')),
                'horse_id': self._sanitize_value(record.get('horse_id')),
                'bookmaker_id': self._sanitize_value(record.get('bookmaker_id')),

                # Race metadata
                'race_date': self._sanitize_value(record.get('race_date')),
                'race_time': self._sanitize_value(record.get('race_time')),
                'off_dt': self._sanitize_value(record.get('off_dt')),
                'course': self._sanitize_value(record.get('course')),
                'race_name': self._sanitize_value(record.get('race_name')),
                'race_class': self._sanitize_value(record.get('race_class')),
                'race_type': self._sanitize_value(record.get('race_type')),
                'distance': self._sanitize_value(record.get('distance')),
                'going': self._sanitize_value(record.get('going')),
                'runners': self._sanitize_value(record.get('runners'), 'int'),

                # Horse metadata
                'horse_name': self._sanitize_value(record.get('horse_name')),
                'horse_number': self._sanitize_value(record.get('horse_number'), 'int'),
                'jockey': self._sanitize_value(record.get('jockey')),
                'trainer': self._sanitize_value(record.get('trainer')),
                'draw': self._sanitize_value(record.get('draw'), 'int'),
                'weight': self._sanitize_value(record.get('weight')),
                'age': self._sanitize_value(record.get('age'), 'int'),
                'form': self._sanitize_value(record.get('form')),

                # Bookmaker information
                'bookmaker_name': self._sanitize_value(record.get('bookmaker_name')),
                'bookmaker_type': self._sanitize_value(record.get('bookmaker_type')),
                'market_type': 'WIN',  # Default to WIN market

                # Odds data (fixed odds only)
                'odds_decimal': self._sanitize_value(record.get('odds_decimal'), 'float'),
                'odds_fractional': self._sanitize_value(record.get('odds_fractional')),

                # Status
                'market_status': record.get('market_status', 'OPEN'),
                'in_play': record.get('in_play', False),

                # Timestamps
                'odds_timestamp': odds_timestamp,
                'updated_at': datetime.now().isoformat(),
                'fetched_at': datetime.now().isoformat()  # Always update fetched_at to show last check time
            }

            # Validate required fields (matching NOT NULL constraints in schema)
            required_fields = {
                'race_id': prepared.get('race_id'),
                'horse_id': prepared.get('horse_id'),
                'bookmaker_id': prepared.get('bookmaker_id'),
                'race_date': prepared.get('race_date'),
                'course': prepared.get('course'),
                'horse_name': prepared.get('horse_name'),
                'bookmaker_name': prepared.get('bookmaker_name'),
                'odds_timestamp': prepared.get('odds_timestamp')
            }

            missing_fields = [k for k, v in required_fields.items() if not v]
            if missing_fields:
                logger.warning(f"⚠️  Record missing required fields: {missing_fields}")
                logger.warning(f"   Horse: {prepared.get('horse_name', 'unknown')}")
                return None

            return prepared

        except Exception as e:
            logger.error(f"Error preparing live record: {e}")
            return None

    def _upsert_batch(self, records: List[Dict], count_in_stats: bool = True):
        """
        Upsert a batch of records to ra_odds_live

        Args:
            records: List of prepared records to upsert
            count_in_stats: If False, don't add to updated count (already counted elsewhere)
        """
        try:
            # Log sample for first batch only (debugging)
            total_processed = self.stats['updated'] + self.stats['inserted']
            if total_processed == 0 and records:
                sample = records[0]
                logger.info(f"💾 First batch sample: {sample.get('horse_name')} @ {sample.get('course')} - {sample.get('bookmaker_name')} - {sample.get('odds_decimal')}")

            # Try upsert with conflict resolution
            response = self.client.table('ra_odds_live').upsert(
                records,
                on_conflict='race_id,horse_id,bookmaker_id'
            ).execute()

            if response.data:
                count = len(response.data)
                if count_in_stats:
                    self.stats['updated'] += count
                # Only log every 500 records to reduce noise
                total_after = self.stats['updated'] + self.stats['inserted']
                if total_after % 500 < count or total_after < 100:
                    logger.info(f"✅ Processed {total_after} records so far ({self.stats['inserted']} new, {self.stats['updated']} updated)...")
            else:
                logger.warning(f"⚠️  Upsert returned no data for {len(records)} records")
                logger.warning(f"   This could mean:")
                logger.warning(f"     - Records were updated but Supabase didn't return them")
                logger.warning(f"     - There was a schema mismatch")
                logger.warning(f"     - Database constraints prevented insertion")

        except Exception as e:
            logger.error(f"❌ Upsert error to ra_odds_live: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Error details: {str(e)}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")

            # Try without on_conflict if that's the issue
            try:
                logger.info("Retrying upsert without on_conflict parameter...")
                response = self.client.table('ra_odds_live').upsert(records).execute()
                if response.data:
                    count = len(response.data)
                    if count_in_stats:
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