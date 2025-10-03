#!/usr/bin/env python3
"""
Live Odds Cron Scheduler
Smart scheduling based on race proximity:
- 5 minutes before race: every 10 seconds
- 30 minutes before: every 1 minute
- 2 hours before: every 5 minutes
- Otherwise: check every 15 minutes for upcoming races
"""

import os
import sys
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pytz

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from live_odds_fetcher import LiveOddsFetcher
from live_odds_client import LiveOddsSupabaseClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cron_live.log')
    ]
)
logger = logging.getLogger(__name__)

# Import monitor
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

# UK timezone for race times
UK_TZ = pytz.timezone('Europe/London')


class LiveOddsScheduler:
    """Smart scheduler for live odds fetching based on race proximity"""

    def __init__(self):
        """Initialize scheduler with fetcher and client"""
        self.fetcher = LiveOddsFetcher()
        self.client = LiveOddsSupabaseClient()

        # Scheduling intervals (in seconds)
        self.INTERVAL_IMMINENT = 10      # 5 min before race
        self.INTERVAL_SOON = 60          # 30 min before race
        self.INTERVAL_UPCOMING = 300     # 2 hours before race
        self.INTERVAL_CHECK = 900        # Default check interval (15 min)

        # Time thresholds (in minutes)
        self.THRESHOLD_IMMINENT = 5
        self.THRESHOLD_SOON = 30
        self.THRESHOLD_UPCOMING = 120

        self.last_fetch = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5

        # Disable monitor server in production worker mode
        MONITOR_ENABLED_ENV = os.getenv('MONITOR_ENABLED', 'false').lower() == 'true'

        if MONITOR_ENABLED and MONITOR_ENABLED_ENV:
            logger.info("🌐 Starting monitor server on port 5000...")
            start_monitor_server(port=5000)
            logger.info("✅ Monitor server started")
            logger.info("📊 Updating initial stats...")
            update_stats(status='running')
            add_activity("Live odds scheduler initialized")
            logger.info("✅ Monitor initialized and ready")
        else:
            logger.info("⚠️ Monitor server disabled (Render.com worker mode)")

    def get_upcoming_races(self) -> List[Dict]:
        """Get races for today and tomorrow (for live odds)"""
        try:
            today = datetime.now(UK_TZ).date()
            tomorrow = today + timedelta(days=1)

            races = []

            # Fetch today's races
            today_str = today.strftime('%Y-%m-%d')
            today_races = self.fetcher._fetch_races_for_date(today_str)
            if today_races:
                races.extend(today_races)
                logger.info(f"📅 Found {len(today_races)} races for TODAY ({today_str})")

            # Fetch tomorrow's races
            tomorrow_str = tomorrow.strftime('%Y-%m-%d')
            tomorrow_races = self.fetcher._fetch_races_for_date(tomorrow_str)
            if tomorrow_races:
                races.extend(tomorrow_races)
                logger.info(f"📅 Found {len(tomorrow_races)} races for TOMORROW ({tomorrow_str})")

            logger.info(f"✅ Total upcoming races (today + tomorrow): {len(races)}")
            return races

        except Exception as e:
            logger.error(f"Error fetching upcoming races: {e}")
            return []

    def calculate_minutes_until_race(self, off_dt: str) -> float:
        """Calculate minutes until race starts"""
        try:
            # Parse race time (format: 2025-09-30T14:30:00+01:00)
            race_time = datetime.fromisoformat(off_dt.replace('Z', '+00:00'))
            now = datetime.now(race_time.tzinfo)
            delta = race_time - now
            return delta.total_seconds() / 60
        except Exception as e:
            logger.error(f"Error calculating time until race: {e}")
            return float('inf')

    def get_optimal_interval(self, races: List[Dict]) -> Tuple[int, str]:
        """Determine optimal fetch interval based on nearest race"""
        if not races:
            return self.INTERVAL_CHECK, "No races scheduled"

        # Find the nearest race
        nearest_race = None
        min_minutes = float('inf')

        for race in races:
            off_dt = race.get('off_dt')
            if not off_dt:
                continue

            minutes_until = self.calculate_minutes_until_race(off_dt)

            # Skip races that have already started
            if minutes_until < -10:  # 10 min grace period
                continue

            if minutes_until < min_minutes:
                min_minutes = minutes_until
                nearest_race = race

        if nearest_race is None:
            return self.INTERVAL_CHECK, "No upcoming races"

        # Determine interval based on proximity
        race_name = nearest_race.get('race_name', 'Unknown')
        course = nearest_race.get('course', 'Unknown')

        if min_minutes <= self.THRESHOLD_IMMINENT:
            return self.INTERVAL_IMMINENT, f"IMMINENT: {course} {race_name} in {min_minutes:.1f} min"
        elif min_minutes <= self.THRESHOLD_SOON:
            return self.INTERVAL_SOON, f"SOON: {course} {race_name} in {min_minutes:.1f} min"
        elif min_minutes <= self.THRESHOLD_UPCOMING:
            return self.INTERVAL_UPCOMING, f"UPCOMING: {course} {race_name} in {min_minutes:.1f} min"
        else:
            return self.INTERVAL_CHECK, f"Next race: {course} {race_name} in {min_minutes:.1f} min"

    def fetch_and_store_odds(self, races: List[Dict]) -> Dict[str, int]:
        """Fetch odds for all races and store in database"""
        stats = {
            'races_processed': 0,
            'horses_processed': 0,
            'odds_stored': 0,
            'errors': 0
        }

        all_odds_records = []
        bookmakers_seen = set()

        try:
            for race in races:
                race_id = race.get('race_id')
                if not race_id:
                    continue

                # Get runners for this race
                runners = race.get('runners', [])

                for runner in runners:
                    horse_id = runner.get('horse_id')
                    if not horse_id:
                        continue

                    try:
                        # Fetch odds for this horse/race combination (returns list of OddsData objects)
                        odds_list = self.fetcher.fetch_live_odds(race_id, horse_id)

                        if odds_list:
                            logger.debug(f"   📊 Found {len(odds_list)} odds for {runner.get('horse')} in race {race_id}")
                            # Convert OddsData objects to dict records for database
                            for odds in odds_list:
                                record = {
                                    'race_id': race_id,
                                    'horse_id': horse_id,
                                    'race_date': race.get('race_date'),
                                    'race_time': race.get('off_time'),
                                    'off_dt': race.get('off_dt'),
                                    'course': race.get('course'),
                                    'race_name': race.get('race_name'),
                                    'race_class': race.get('race_class'),
                                    'race_type': race.get('race_type'),
                                    'distance': race.get('distance'),
                                    'going': race.get('going'),
                                    'runners': len(runners),
                                    'horse_name': runner.get('horse'),
                                    'horse_number': runner.get('number'),
                                    'jockey': runner.get('jockey'),
                                    'trainer': runner.get('trainer'),
                                    'draw': runner.get('draw'),
                                    'weight': runner.get('weight'),
                                    'age': runner.get('age'),
                                    'form': runner.get('form'),
                                    'bookmaker_id': odds.bookmaker_id,
                                    'bookmaker_name': odds.bookmaker_name,
                                    'bookmaker_type': odds.bookmaker_type,
                                    'odds_decimal': odds.odds_decimal,
                                    'odds_fractional': odds.odds_fractional,
                                    'back_price': odds.back_price,
                                    'lay_price': odds.lay_price,
                                    'back_size': odds.back_size,
                                    'lay_size': odds.lay_size,
                                    'back_prices': odds.back_prices,
                                    'lay_prices': odds.lay_prices,
                                    'total_matched': odds.total_matched,
                                    'market_status': odds.market_status,
                                    'in_play': odds.in_play,
                                    'odds_timestamp': odds.odds_timestamp
                                }
                                all_odds_records.append(record)
                                stats['odds_stored'] += 1
                                bookmakers_seen.add(odds.bookmaker_name)

                            stats['horses_processed'] += 1

                    except Exception as e:
                        logger.error(f"Error processing {race_id}/{horse_id}: {e}")
                        stats['errors'] += 1

                stats['races_processed'] += 1

                # Update monitor with current race
                if MONITOR_ENABLED:
                    current_race_name = f"{race.get('course', 'Unknown')} {race.get('off_time', '')}"
                    update_stats(
                        races_processed=stats['races_processed'],
                        horses_processed=stats['horses_processed'],
                        odds_stored=stats['odds_stored'],
                        errors=stats['errors'],
                        current_race=current_race_name,
                        bookmakers_active=list(bookmakers_seen)
                    )

            # Store all odds in database in one batch
            if all_odds_records:
                logger.info(f"💾 Attempting to store {len(all_odds_records)} odds records to Supabase table 'ra_odds_live'...")
                logger.info(f"   🔌 Database URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
                logger.info(f"   📝 Sample record: race_id={all_odds_records[0].get('race_id')}, horse={all_odds_records[0].get('horse_name')}, bookmaker={all_odds_records[0].get('bookmaker_name')}")

                try:
                    db_stats = self.client.update_live_odds(all_odds_records)
                    logger.info(f"✅ DATABASE INSERT SUCCESS: {db_stats}")
                    logger.info(f"   📊 Records inserted/updated: {db_stats.get('updated', 0)}")
                    logger.info(f"   ❌ Records failed: {db_stats.get('failed', 0)}")

                    if MONITOR_ENABLED:
                        add_activity(f"Stored {len(all_odds_records)} odds to ra_odds_live (updated: {db_stats.get('updated', 0)})")
                except Exception as db_error:
                    logger.error(f"❌ DATABASE INSERT FAILED: {db_error}")
                    logger.error(f"   Error type: {type(db_error).__name__}")
                    import traceback
                    logger.error(f"   Traceback: {traceback.format_exc()}")
            else:
                logger.warning("⚠️  No odds records collected - nothing to store in database")
                logger.warning(f"   Races processed: {stats['races_processed']}, Horses: {stats['horses_processed']}, Errors: {stats['errors']}")

            return stats

        except Exception as e:
            logger.error(f"Error in fetch_and_store_odds: {e}")
            stats['errors'] += 1
            return stats

    def run_fetch_cycle(self) -> bool:
        """Run one fetch cycle, return True if successful"""
        try:
            logger.info("Starting fetch cycle...")

            # Get upcoming races
            races = self.get_upcoming_races()

            if not races:
                logger.info("No upcoming races found")
                return True

            logger.info(f"Found {len(races)} races to process")

            # Fetch and store odds
            stats = self.fetch_and_store_odds(races)

            logger.info(
                f"Fetch cycle complete: "
                f"{stats['races_processed']} races, "
                f"{stats['horses_processed']} horses, "
                f"{stats['odds_stored']} odds stored, "
                f"{stats['errors']} errors"
            )

            self.last_fetch = datetime.now(UK_TZ)
            self.consecutive_errors = 0
            return True

        except Exception as e:
            logger.error(f"Error in fetch cycle: {e}")
            self.consecutive_errors += 1
            return False

    def run_continuous(self):
        """Run scheduler continuously with smart intervals"""
        logger.info("=" * 80)
        logger.info("🚀 STARTING LIVE ODDS SCHEDULER")
        logger.info("=" * 80)
        logger.info(f"Intervals: Imminent={self.INTERVAL_IMMINENT}s, "
                   f"Soon={self.INTERVAL_SOON}s, "
                   f"Upcoming={self.INTERVAL_UPCOMING}s, "
                   f"Check={self.INTERVAL_CHECK}s")
        logger.info("=" * 80)

        if MONITOR_ENABLED:
            add_activity("🚀 Live odds scheduler started - running first fetch immediately")

        # Run IMMEDIATE first fetch on startup
        logger.info("\n🎯 RUNNING IMMEDIATE INITIAL FETCH...")
        try:
            initial_success = self.run_fetch_cycle()
            if initial_success:
                logger.info("✅ Initial fetch complete - entering continuous mode")
            else:
                logger.warning("⚠️ Initial fetch had issues - will retry in loop")
        except Exception as e:
            logger.error(f"❌ Error in initial fetch: {e}")
            logger.info("⚠️ Will retry in continuous loop - not fatal, continuing...")
            # Don't crash - continue to main monitoring loop

        # Now enter continuous loop
        logger.info("\n🔄 ENTERING CONTINUOUS MODE\n")

        while True:
            try:
                # Check if we should stop due to too many errors
                if self.consecutive_errors >= self.max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({self.consecutive_errors}), stopping")
                    break

                # Get upcoming races to determine interval
                races = self.get_upcoming_races()
                interval, reason = self.get_optimal_interval(races)

                logger.info(f"Next interval: {interval}s - {reason}")

                # Sleep FIRST, then fetch (we already did initial fetch)
                logger.info(f"Sleeping for {interval} seconds...")
                time.sleep(interval)

                # Run fetch cycle
                success = self.run_fetch_cycle()

                if not success:
                    logger.warning(f"Fetch cycle failed, consecutive errors: {self.consecutive_errors}")

            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                self.consecutive_errors += 1
                time.sleep(60)  # Wait 1 minute before retry


def main():
    """Main entry point"""
    scheduler = LiveOddsScheduler()
    scheduler.run_continuous()


if __name__ == '__main__':
    main()
