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
from dateutil import parser as date_parser
from zoneinfo import ZoneInfo

from .live_odds_fetcher import LiveOddsFetcher
from .live_odds_client import LiveOddsSupabaseClient

# Setup logging first (before using logger)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cron_live.log')
    ]
)
logger = logging.getLogger('LIVE_ODDS')  # Clear service name

# Import statistics updater
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from odds_statistics.update_stats import update_statistics
    STATS_ENABLED = True
    logger.info("✅ Statistics updater imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Statistics updater not available: {e}")
    STATS_ENABLED = False
    def update_statistics(*args, **kwargs):
        pass

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

    def get_upcoming_races(self, limit_races: int = None) -> List[Dict]:
        """Get upcoming races for today and tomorrow to collect odds data throughout the day"""
        try:
            today = datetime.now(UK_TZ).date()
            end_date = today + timedelta(days=1)  # Today + tomorrow

            races = []
            current_date = today

            logger.info(f"📅 Fetching races from {today} to {end_date}...")
            if limit_races:
                logger.info(f"   ⚠️  Limiting to first {limit_races} races for testing")

            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                day_races = self.fetcher._fetch_races_for_date(date_str)
                if day_races:
                    # Filter to only races that haven't started yet (or just started)
                    now = datetime.now(UK_TZ)
                    upcoming = []
                    for race in day_races:
                        off_dt_str = race.get('off_dt')
                        if off_dt_str:
                            try:
                                # Parse race time
                                race_time = date_parser.parse(off_dt_str)
                                # Include all upcoming races for today/tomorrow
                                # Only exclude races that have already started
                                time_until_race = (race_time - now).total_seconds() / 60  # minutes
                                if time_until_race >= 0:  # No upper limit - collect odds all day
                                    upcoming.append(race)
                            except:
                                # If can't parse time, include it anyway
                                upcoming.append(race)
                        else:
                            # No time info, include it
                            upcoming.append(race)

                    if upcoming:
                        races.extend(upcoming)
                        logger.info(f"  Found {len(upcoming)}/{len(day_races)} upcoming races for {date_str}")
                    elif day_races:
                        logger.info(f"  Skipped {len(day_races)} races for {date_str} (all finished)")

                # Check if we've hit the limit
                if limit_races and len(races) >= limit_races:
                    logger.info(f"  ⚠️  Reached race limit ({limit_races}), stopping date fetch")
                    races = races[:limit_races]
                    break

                current_date += timedelta(days=1)

            logger.info(f"📊 Total upcoming races: {len(races)}")
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

            # Skip races that have already started (stop updating once race begins)
            if minutes_until < 0:  # Race has started
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

        logger.info(f"")
        logger.info(f"=" * 80)
        logger.info(f"📊 STAGE 1: PARSING EMBEDDED ODDS FROM API DATA")
        logger.info(f"=" * 80)
        logger.info(f"🔍 Processing {len(races)} races with embedded odds...")
        logger.info(f"")

        try:
            for race_idx, race in enumerate(races, 1):
                race_id = race.get('race_id')
                if not race_id:
                    logger.debug(f"  [{race_idx}/{len(races)}] Skipping race - no race_id")
                    continue

                # Get runners for this race
                runners = race.get('runners', [])

                # Enhanced logging
                logger.info(f"  [{race_idx}/{len(races)}] {race.get('course')} {race.get('off_time')}")
                logger.info(f"      Race ID: {race_id}")
                logger.info(f"      Runners: {len(runners)}")

                if len(runners) == 0:
                    logger.warning(f"      ⚠️  NO RUNNERS IN THIS RACE!")
                    continue

                if race_idx == 1:
                    # Show structure of first runner's odds
                    first_runner = runners[0]
                    logger.info(f"      First runner: {first_runner.get('horse', 'Unknown')}")
                    logger.info(f"      Embedded odds field: {'odds' in first_runner}")
                    if 'odds' in first_runner:
                        odds_count = len(first_runner.get('odds', []))
                        logger.info(f"      Number of bookmakers: {odds_count}")
                        if odds_count > 0:
                            sample_bookie = first_runner['odds'][0]
                            logger.info(f"      Sample bookmaker: {sample_bookie.get('bookmaker', 'N/A')} = {sample_bookie.get('decimal', 'N/A')}")

                if not runners:
                    logger.warning(f"  ⚠️  Skipping race {race_id} - no runners")
                    continue

                horses_in_race = 0
                for runner in runners:
                    horse_id = runner.get('horse_id')
                    horse_name = runner.get('horse', 'Unknown')
                    if not horse_id:
                        logger.warning(f"      ⚠️  Runner missing horse_id: {horse_name}")
                        continue

                    horses_in_race += 1

                    try:
                        # Parse embedded odds from runner data (NO API CALL)
                        logger.debug(f"      → Parsing embedded odds for: {horse_name}")
                        odds_list = self.fetcher.parse_embedded_odds(runner, race_id)

                        if race_idx <= 3 and horses_in_race == 1:
                            logger.info(f"      → First horse '{horse_name}': {len(odds_list)} bookmakers")

                        if odds_list:
                            # Log first successful odds parse
                            if len(all_odds_records) == 0:
                                logger.info(f"")
                                logger.info(f"    ✅ FIRST ODDS FOUND!")
                                logger.info(f"       Horse: {horse_name}")
                                logger.info(f"       Bookmakers: {len(odds_list)}")
                                logger.info(f"       Sample: {odds_list[0].bookmaker_name} = {odds_list[0].odds_decimal}")
                                logger.info(f"")

                            # Convert off_dt to UK time for race_time
                            race_time_uk = None
                            off_dt_str = race.get('off_dt')
                            if off_dt_str:
                                try:
                                    # Parse UTC time and convert to UK timezone
                                    off_dt_utc = datetime.fromisoformat(off_dt_str.replace('Z', '+00:00'))
                                    off_dt_uk = off_dt_utc.astimezone(ZoneInfo('Europe/London'))
                                    race_time_uk = off_dt_uk.strftime('%H:%M:%S')
                                except Exception as e:
                                    logger.warning(f"Failed to convert off_dt to UK time: {e}")
                                    race_time_uk = race.get('off_time')  # Fallback to API value
                            else:
                                race_time_uk = race.get('off_time')  # Fallback if no off_dt

                            # Convert OddsData objects to dict records for database
                            for odds in odds_list:
                                record = {
                                    'race_id': race_id,
                                    'horse_id': horse_id,
                                    'race_date': race.get('race_date'),
                                    'race_time': race_time_uk,
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
                                    'market_status': odds.market_status,
                                    'in_play': odds.in_play,
                                    'odds_timestamp': odds.odds_timestamp
                                }
                                all_odds_records.append(record)
                                stats['odds_stored'] += 1
                                bookmakers_seen.add(odds.bookmaker_name)

                            stats['horses_processed'] += 1
                        else:
                            if race_idx <= 3:
                                logger.warning(f"      ⚠️  No embedded odds for {horse_name}")

                    except Exception as e:
                        logger.error(f"    ❌ Error parsing odds for {horse_name}: {e}")
                        import traceback
                        logger.error(f"    Traceback: {traceback.format_exc()}")
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

            # Log processing summary
            logger.info(f"")
            logger.info(f"=" * 80)
            logger.info(f"📊 STAGE 1 COMPLETE - PARSING SUMMARY:")
            logger.info(f"   Races processed: {stats['races_processed']}/{len(races)}")
            logger.info(f"   Horses processed: {stats['horses_processed']}")
            logger.info(f"   Odds records collected: {len(all_odds_records)}")
            logger.info(f"   Unique bookmakers: {len(bookmakers_seen)}")
            if bookmakers_seen:
                logger.info(f"   Bookmakers: {', '.join(sorted(bookmakers_seen))}")
            logger.info(f"   Errors: {stats['errors']}")
            logger.info(f"=" * 80)
            logger.info(f"")

            # Store all odds in database in one batch
            if all_odds_records:
                logger.info(f"")
                logger.info(f"=" * 80)
                logger.info(f"📊 STAGE 2: INSERTING TO SUPABASE")
                logger.info(f"=" * 80)
                logger.info(f"💾 Sending {len(all_odds_records)} records to ra_odds_live table...")
                logger.info(f"   Sample record:")
                sample = all_odds_records[0]
                logger.info(f"     Race: {sample.get('course')} - {sample.get('race_name')}")
                logger.info(f"     Horse: {sample.get('horse_name')}")
                logger.info(f"     Bookmaker: {sample.get('bookmaker_name')}")
                logger.info(f"     Odds: {sample.get('odds_decimal')}")
                logger.info(f"")

                try:
                    db_stats = self.client.update_live_odds(all_odds_records)
                    logger.info(f"")
                    logger.info(f"=" * 80)
                    logger.info(f"✅ STAGE 2 COMPLETE - DATABASE INSERT SUCCESSFUL")
                    logger.info(f"   Records inserted/updated: {db_stats.get('updated', 0)}")
                    logger.info(f"   Unique races: {db_stats.get('races', 'N/A')}")
                    logger.info(f"   Unique horses: {db_stats.get('horses', 'N/A')}")
                    logger.info(f"   Unique bookmakers: {db_stats.get('bookmakers', 'N/A')}")
                    logger.info(f"   Errors: {db_stats.get('errors', 0)}")
                    logger.info(f"=" * 80)
                    logger.info(f"")

                    if MONITOR_ENABLED:
                        add_activity(f"✅ Stored {len(all_odds_records)} odds (updated: {db_stats.get('updated', 0)})")
                except Exception as e:
                    logger.error(f"")
                    logger.error(f"=" * 80)
                    logger.error(f"❌ STAGE 2 FAILED - DATABASE INSERT ERROR")
                    logger.error(f"   Error: {e}")
                    logger.error(f"   Error type: {type(e).__name__}")
                    import traceback
                    logger.error(f"   Traceback:\n{traceback.format_exc()}")
                    logger.error(f"=" * 80)
                    logger.error(f"")
                    raise
            else:
                logger.warning(f"")
                logger.warning(f"=" * 80)
                logger.warning(f"⚠️  NO ODDS RECORDS COLLECTED - NOTHING TO INSERT")
                logger.warning(f"=" * 80)
                logger.warning(f"   This likely means:")
                logger.warning(f"     1. No embedded odds in API racecard responses")
                logger.warning(f"     2. All races have no 'odds' field in runner data")
                logger.warning(f"     3. Races may be too far in future or already finished")
                logger.warning(f"=" * 80)
                logger.warning(f"")

            return stats

        except Exception as e:
            logger.error(f"Error in fetch_and_store_odds: {e}")
            stats['errors'] += 1
            return stats

    def run_fetch_cycle(self) -> bool:
        """Run one fetch cycle, return True if successful"""
        try:
            logger.info("Starting fetch cycle...")

            # Get upcoming races (with optional limit for testing)
            test_limit = int(os.getenv('TEST_RACE_LIMIT', '0'))
            races = self.get_upcoming_races(limit_races=test_limit if test_limit > 0 else None)

            if not races:
                logger.info("No upcoming races found")
                return True

            logger.info(f"Found {len(races)} races to process")

            # Fetch and store odds
            logger.info(f"🔄 Starting to fetch and store odds for {len(races)} races...")
            try:
                stats = self.fetch_and_store_odds(races)

                logger.info("")
                logger.info("=" * 80)
                logger.info("✅ FETCH CYCLE COMPLETE")
                logger.info(f"   Races processed: {stats['races_processed']}")
                logger.info(f"   Horses processed: {stats['horses_processed']}")
                logger.info(f"   Odds stored: {stats['odds_stored']}")
                logger.info(f"   Errors: {stats['errors']}")
                logger.info("=" * 80)
                logger.info("")
            except Exception as e:
                logger.error(f"❌ CRITICAL ERROR in fetch_and_store_odds: {e}")
                import traceback
                logger.error(f"Traceback:\n{traceback.format_exc()}")
                stats = {'races_processed': 0, 'horses_processed': 0, 'odds_stored': 0, 'errors': 1}

            self.last_fetch = datetime.now(UK_TZ)
            self.consecutive_errors = 0

            # Update statistics after successful fetch cycle
            if STATS_ENABLED and stats.get('odds_stored', 0) > 0:
                logger.info("📊 Updating live odds statistics...")
                try:
                    update_statistics(table='live', save_to_file=True)
                    logger.info("✅ Statistics updated successfully")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update statistics: {e}")

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
