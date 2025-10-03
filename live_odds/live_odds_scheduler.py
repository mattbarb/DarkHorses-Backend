"""
Live Odds Scheduler
Smart scheduling system that updates odds more frequently as races approach
"""

import os
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from pathlib import Path

from live_odds_fetcher import LiveOddsFetcher
from live_odds_client import LiveOddsSupabaseClient

# Load environment - optional for Render.com
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    # Running on Render.com - use system environment variables
    pass

logger = logging.getLogger(__name__)


class LiveOddsScheduler:
    """Smart scheduler for live odds updates based on time to race"""

    def __init__(self):
        self.fetcher = LiveOddsFetcher()
        self.db_client = LiveOddsSupabaseClient()
        self.running = True

        # Update intervals based on time to race (in seconds)
        self.update_intervals = {
            'far': 300,      # > 2 hours: every 5 minutes
            'medium': 120,   # 1-2 hours: every 2 minutes
            'near': 60,      # 30-60 mins: every 1 minute
            'close': 30,     # 5-30 mins: every 30 seconds
            'imminent': 10,  # < 5 mins: every 10 seconds
            'live': 5        # In-play: every 5 seconds
        }

        # Track last update time for each race
        self.race_last_update = {}

    def get_update_interval(self, minutes_to_start: float) -> int:
        """Get appropriate update interval based on time to race start"""
        if minutes_to_start < 0:
            return self.update_intervals['live']  # Race has started (in-play)
        elif minutes_to_start < 5:
            return self.update_intervals['imminent']
        elif minutes_to_start < 30:
            return self.update_intervals['close']
        elif minutes_to_start < 60:
            return self.update_intervals['near']
        elif minutes_to_start < 120:
            return self.update_intervals['medium']
        else:
            return self.update_intervals['far']

    def should_update_race(self, race_id: str, off_dt: datetime) -> bool:
        """Check if a race needs updating based on its schedule"""
        now = datetime.now(off_dt.tzinfo) if off_dt.tzinfo else datetime.now()
        minutes_to_start = (off_dt - now).total_seconds() / 60

        # Don't update races more than 4 hours away
        if minutes_to_start > 240:
            return False

        # Don't update races that finished more than 30 mins ago
        if minutes_to_start < -30:
            return False

        # Get required interval
        required_interval = self.get_update_interval(minutes_to_start)

        # Check last update time
        last_update = self.race_last_update.get(race_id)
        if last_update:
            seconds_since_update = (now - last_update).total_seconds()
            return seconds_since_update >= required_interval

        return True  # First time seeing this race

    def fetch_race_odds(self, race: Dict) -> List[Dict]:
        """Fetch odds for all horses in a race from all bookmakers"""
        race_id = race.get('id_race')
        all_odds = []

        logger.info(f"Fetching odds for {race.get('course')} - {race.get('race_name')}")

        # Extract race metadata
        race_meta = {
            'race_id': race_id,
            'race_date': race.get('date'),
            'race_time': race.get('off_time'),
            'off_dt': race.get('off_dt'),
            'course': race.get('course'),
            'race_name': race.get('race_name'),
            'race_class': race.get('race_class'),
            'race_type': race.get('type'),
            'distance': race.get('distance'),
            'going': race.get('going'),
            'runners': race.get('runners')
        }

        # Fetch odds for each horse
        for horse in race.get('horses', []):
            horse_id = horse.get('id_horse')

            # Get horse metadata
            horse_meta = {
                **race_meta,
                'horse_id': horse_id,
                'horse_name': horse.get('horse'),
                'horse_number': horse.get('number'),
                'jockey': horse.get('jockey'),
                'trainer': horse.get('trainer'),
                'draw': horse.get('draw'),
                'weight': horse.get('weight'),
                'age': horse.get('age'),
                'form': horse.get('form')
            }

            # Fetch odds from all bookmakers
            try:
                odds_list = self.fetcher.fetch_live_odds(race_id, horse_id)

                for odds in odds_list:
                    record = {
                        **horse_meta,
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
                    all_odds.append(record)

            except Exception as e:
                logger.error(f"Error fetching odds for {horse_id}: {e}")

        # Update last fetch time
        self.race_last_update[race_id] = datetime.now()

        return all_odds

    def update_live_odds(self):
        """Main update cycle for all upcoming races"""
        logger.info("Starting live odds update cycle")

        # Get races in next 4 hours
        self.fetcher.hours_ahead = 4
        races = self.fetcher.fetch_upcoming_races()

        if not races:
            logger.info("No upcoming races found")
            return

        logger.info(f"Found {len(races)} upcoming races")

        # Filter races that need updating
        races_to_update = []
        for race in races:
            off_dt_str = race.get('off_dt')
            if off_dt_str:
                try:
                    off_dt = datetime.fromisoformat(off_dt_str.replace('Z', '+00:00'))
                    if self.should_update_race(race.get('id_race'), off_dt):
                        races_to_update.append(race)
                except:
                    pass

        if not races_to_update:
            logger.info("No races need updating at this time")
            return

        logger.info(f"Updating odds for {len(races_to_update)} races")

        # Fetch odds for each race
        all_race_odds = []
        bookmakers_found = set()

        for race in races_to_update:
            race_odds = self.fetch_race_odds(race)
            all_race_odds.extend(race_odds)

            # Track bookmakers
            for odds in race_odds:
                bookmakers_found.add(odds['bookmaker_id'])

        # Save to database
        if all_race_odds:
            logger.info(f"Saving {len(all_race_odds)} odds records from {len(bookmakers_found)} bookmakers")
            stats = self.db_client.update_live_odds(all_race_odds)

            # Save statistics
            self.db_client.save_statistics({
                'races_processed': len(races_to_update),
                'odds_fetched': len(all_race_odds),
                'bookmakers_found': list(bookmakers_found),
                'duration_seconds': 0  # Would need timing logic
            })

            logger.info(f"Update complete: {stats}")

    def run_continuous(self):
        """Run continuous updates with smart scheduling"""
        logger.info("Starting continuous live odds updates")

        while self.running:
            try:
                # Run update cycle
                self.update_live_odds()

                # Clean up old races from tracking
                now = datetime.now()
                old_races = [
                    race_id for race_id, last_update in self.race_last_update.items()
                    if (now - last_update).total_seconds() > 3600  # 1 hour old
                ]
                for race_id in old_races:
                    del self.race_last_update[race_id]

                # Sleep briefly before next check
                time.sleep(5)  # Check every 5 seconds for races needing updates

            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in update cycle: {e}")
                time.sleep(10)  # Back off on error

    def get_schedule_info(self):
        """Get information about current update schedule"""
        info = []
        now = datetime.now()

        for race_id, last_update in self.race_last_update.items():
            seconds_ago = (now - last_update).total_seconds()
            info.append({
                'race_id': race_id,
                'last_update': last_update.isoformat(),
                'seconds_ago': int(seconds_ago)
            })

        return {
            'tracked_races': len(self.race_last_update),
            'races': info,
            'update_intervals': self.update_intervals
        }


def main():
    """Main entry point for scheduler"""
    import sys
    from utils.logger import setup_logging

    # Setup logging
    setup_logging()

    print("="*60)
    print("LIVE ODDS SCHEDULER")
    print("Smart scheduling based on time to race")
    print("="*60)
    print("\nUpdate Schedule:")
    print("  > 2 hours before:  Every 5 minutes")
    print("  1-2 hours before:  Every 2 minutes")
    print("  30-60 mins before: Every 1 minute")
    print("  5-30 mins before:  Every 30 seconds")
    print("  < 5 mins before:   Every 10 seconds")
    print("  In-play:           Every 5 seconds")
    print("\nPress Ctrl+C to stop")
    print("="*60)

    # Create and run scheduler
    scheduler = LiveOddsScheduler()

    try:
        scheduler.run_continuous()
    except KeyboardInterrupt:
        print("\n\nScheduler stopped")
        sys.exit(0)


if __name__ == '__main__':
    main()