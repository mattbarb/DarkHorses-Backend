"""
Races Reference Data Fetcher
Fetches race and runner data from Racing API racecards endpoint
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config.config import get_config
from utils.logger import get_logger
from utils.api_client import RacingAPIClient
from utils.supabase_client import SupabaseReferenceClient

logger = get_logger('races_fetcher')


class RacesFetcher:
    """Fetcher for race and runner reference data from racecards"""

    def __init__(self):
        """Initialize fetcher"""
        self.config = get_config()
        self.api_client = RacingAPIClient(
            username=self.config.api.username,
            password=self.config.api.password,
            base_url=self.config.api.base_url,
            timeout=self.config.api.timeout,
            max_retries=self.config.api.max_retries
        )
        self.db_client = SupabaseReferenceClient(
            url=self.config.supabase.url,
            service_key=self.config.supabase.service_key,
            batch_size=self.config.supabase.batch_size
        )

    def fetch_and_store(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days_back: int = 30,
        region_codes: List[str] = None
    ) -> Dict:
        """
        Fetch racecards from API and store races and runners in database

        Args:
            start_date: Start date (YYYY-MM-DD format). If None, calculated from days_back
            end_date: End date (YYYY-MM-DD format). If None, defaults to today
            days_back: Number of days to go back (default: 30). Ignored if start_date provided
            region_codes: Optional list of region codes to filter (e.g., ['gb', 'ire'])

        Returns:
            Statistics dictionary
        """
        logger.info("Starting races and runners fetch from racecards")
        logger.info(f"Region filtering: {region_codes if region_codes else 'None (all regions)'}")

        # Calculate date range
        if end_date is None:
            end_dt = datetime.utcnow().date()
        else:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

        if start_date is None:
            start_dt = end_dt - timedelta(days=days_back)
        else:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()

        logger.info(f"Fetching racecards from {start_dt} to {end_dt}")

        all_races = []
        all_runners = []
        days_fetched = 0
        days_with_data = 0

        # Iterate day by day (most efficient per API docs)
        current_date = start_dt
        while current_date <= end_dt:
            date_str = current_date.strftime('%Y-%m-%d')
            logger.info(f"Fetching racecards for {date_str}")

            # Fetch racecards for this date
            api_response = self.api_client.get_racecards_pro(
                date=date_str,
                region_codes=region_codes
            )

            if not api_response or 'racecards' not in api_response:
                logger.warning(f"No racecards returned for {date_str}")
                current_date += timedelta(days=1)
                days_fetched += 1
                continue

            racecards = api_response.get('racecards', [])
            if racecards:
                days_with_data += 1
                logger.info(f"Fetched {len(racecards)} races for {date_str}")

                # Process each race
                for racecard in racecards:
                    race_data, runners_data = self._transform_racecard(racecard)
                    if race_data:
                        all_races.append(race_data)
                    if runners_data:
                        all_runners.extend(runners_data)

            days_fetched += 1
            current_date += timedelta(days=1)

        logger.info(f"Total races fetched: {len(all_races)}")
        logger.info(f"Total runners fetched: {len(all_runners)}")
        logger.info(f"Days fetched: {days_fetched}, Days with data: {days_with_data}")

        # Store in database
        results = {}
        if all_races:
            race_stats = self.db_client.insert_races(all_races)
            results['races'] = race_stats
            logger.info(f"Races inserted: {race_stats}")

        if all_runners:
            runner_stats = self.db_client.insert_runners(all_runners)
            results['runners'] = runner_stats
            logger.info(f"Runners inserted: {runner_stats}")

        return {
            'success': True,
            'fetched': len(all_races),
            'inserted': len(all_races),  # For consistency with other fetchers
            'races_fetched': len(all_races),
            'runners_fetched': len(all_runners),
            'races_inserted': results.get('races', {}).get('inserted', 0),
            'runners_inserted': results.get('runners', {}).get('inserted', 0),
            'days_fetched': days_fetched,
            'days_with_data': days_with_data,
            'api_stats': self.api_client.get_stats(),
            'db_stats': results
        }

    def _transform_racecard(self, racecard: Dict) -> tuple:
        """
        Transform API racecard data into database format

        Args:
            racecard: Raw racecard data from API

        Returns:
            Tuple of (race_dict, list_of_runner_dicts)
        """
        # Extract race data - API uses 'race_id' not 'id'
        race_id = racecard.get('race_id')
        if not race_id:
            logger.warning("Racecard missing race_id, skipping")
            return None, None

        # Helper function to convert distance strings to meters
        def parse_distance_meters(dist_str):
            """Convert distance string like '1m', '6f', '2m4f' to meters (approximate)"""
            if not dist_str or not isinstance(dist_str, str):
                return None
            try:
                # Try direct integer conversion first
                return int(dist_str)
            except (ValueError, TypeError):
                # Parse string like "1m", "6f", "2m4f", etc.
                # Note: This is approximate. 1 furlong ≈ 201 meters, 1 mile ≈ 1609 meters
                dist_str = dist_str.lower().strip()
                meters = 0

                # Extract miles
                if 'm' in dist_str:
                    parts = dist_str.split('m')
                    if parts[0]:
                        try:
                            miles = int(parts[0])
                            meters += miles * 1609  # 1 mile ≈ 1609 meters
                            dist_str = parts[1] if len(parts) > 1 else ''
                        except ValueError:
                            pass

                # Extract furlongs
                if 'f' in dist_str:
                    parts = dist_str.split('f')
                    if parts[0]:
                        try:
                            furlongs = int(parts[0])
                            meters += furlongs * 201  # 1 furlong ≈ 201 meters
                        except ValueError:
                            pass

                return meters if meters > 0 else None

        # Helper function to parse prize money
        def parse_prize_money(prize_str):
            """Convert prize string like '£4,187' to numeric"""
            if not prize_str or not isinstance(prize_str, str):
                return None
            try:
                # Remove currency symbols and commas
                cleaned = prize_str.replace('£', '').replace('$', '').replace(',', '').strip()
                return float(cleaned)
            except (ValueError, AttributeError):
                return None

        # Helper function to safely parse integers
        def safe_int(value):
            """Safely convert value to integer, handling strings like '-', 'NR', etc."""
            if value is None:
                return None
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                value = value.strip()
                if value in ('', '-', 'NR', 'N/A', 'DNF', 'PU', 'F', 'UR', 'RO', 'BD'):
                    return None
                try:
                    return int(value)
                except ValueError:
                    return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        # Build race record
        race_record = {
            'race_id': race_id,
            'racing_api_race_id': race_id,
            'is_from_api': True,
            'fetched_at': datetime.utcnow().isoformat(),
            'course_id': racecard.get('course_id'),
            'course_name': racecard.get('course'),
            'region': racecard.get('region'),
            'race_name': racecard.get('race_name'),
            'race_date': racecard.get('date'),  # Changed from 'race_date' to 'date'
            'off_datetime': racecard.get('off_dt'),
            'off_time': racecard.get('off_time'),
            'start_time': racecard.get('start_time'),
            'race_type': racecard.get('type'),
            'race_class': racecard.get('race_class'),
            'distance': racecard.get('distance_f'),  # Numeric furlong value
            'distance_f': racecard.get('distance'),  # String like "1m"
            'distance_meters': parse_distance_meters(racecard.get('distance_round')),
            'age_band': racecard.get('age_band'),
            'surface': racecard.get('surface'),
            'going': racecard.get('going'),
            'track_condition': racecard.get('going_detailed'),
            'weather_conditions': racecard.get('weather'),
            'rail_movements': racecard.get('rail_movements'),
            'stalls_position': racecard.get('stalls_position'),
            'race_status': racecard.get('status'),
            'betting_status': racecard.get('betting_status'),
            'results_status': racecard.get('results_status'),
            'is_abandoned': racecard.get('is_abandoned', False),
            'currency': 'GBP',  # Default currency for UK/IRE races
            'prize_money': parse_prize_money(racecard.get('prize')),
            'total_prize_money': parse_prize_money(racecard.get('total_prize_money')),
            'big_race': racecard.get('big_race', False),
            'field_size': len(racecard.get('runners', [])),
            'live_stream_url': racecard.get('live_stream_url'),
            'replay_url': racecard.get('replay_url'),
            'api_data': racecard,  # Store full API response
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        # Extract runners data
        runners = racecard.get('runners', [])
        runner_records = []

        for idx, runner in enumerate(runners, 1):
            # Generate runner_id from race_id and horse_id (API doesn't provide runner ID)
            horse_id = runner.get('horse_id')
            if not horse_id:
                logger.warning(f"Runner in race {race_id} missing horse_id, skipping")
                continue

            # Create unique runner_id: race_id + horse_id (or use index as fallback)
            runner_id = f"{race_id}_{horse_id}"

            runner_record = {
                'runner_id': runner_id,
                'is_from_api': True,
                'fetched_at': datetime.utcnow().isoformat(),
                'race_id': race_id,
                'racing_api_race_id': race_id,
                'horse_id': runner.get('horse_id'),
                'racing_api_horse_id': runner.get('horse_id'),
                'horse_name': runner.get('horse'),
                'age': safe_int(runner.get('age')),
                'sex': runner.get('sex'),
                'number': safe_int(runner.get('number')),
                'draw': safe_int(runner.get('draw')),
                'stall': safe_int(runner.get('stall')),
                'jockey_id': runner.get('jockey_id'),
                'racing_api_jockey_id': runner.get('jockey_id'),
                'jockey_name': runner.get('jockey'),
                'jockey_claim': runner.get('jockey_claim'),
                'apprentice_allowance': runner.get('jockey_allowance'),
                'trainer_id': runner.get('trainer_id'),
                'racing_api_trainer_id': runner.get('trainer_id'),
                'trainer_name': runner.get('trainer'),
                'owner_id': runner.get('owner_id'),
                'racing_api_owner_id': runner.get('owner_id'),
                'owner_name': runner.get('owner'),
                'weight': runner.get('lbs'),
                'weight_lbs': runner.get('lbs'),  # Use 'lbs' field
                'headgear': runner.get('headgear'),
                # Parse headgear_run string for boolean flags (but don't store headgear_run itself)
                'blinkers': 'b' in (runner.get('headgear_run') or '').lower(),
                'cheekpieces': 'c' in (runner.get('headgear_run') or '').lower(),
                'visor': 'v' in (runner.get('headgear_run') or '').lower(),
                'tongue_tie': 't' in (runner.get('headgear_run') or '').lower(),
                'sire_id': runner.get('sire_id'),
                'sire_name': runner.get('sire'),
                'dam_id': runner.get('dam_id'),
                'dam_name': runner.get('dam'),
                'damsire_id': runner.get('damsire_id'),
                'damsire_name': runner.get('damsire'),
                'form': runner.get('form'),
                'form_string': runner.get('form_string'),
                'days_since_last_run': safe_int(runner.get('days_since_last_run')),
                'last_run_performance': runner.get('last_run'),
                'career_runs': safe_int(runner.get('career_total', {}).get('runs')) if isinstance(runner.get('career_total'), dict) else None,
                'career_wins': safe_int(runner.get('career_total', {}).get('wins')) if isinstance(runner.get('career_total'), dict) else None,
                'career_places': safe_int(runner.get('career_total', {}).get('places')) if isinstance(runner.get('career_total'), dict) else None,
                'prize_money_won': runner.get('prize_money'),
                'official_rating': safe_int(runner.get('ofr')),
                'racing_post_rating': safe_int(runner.get('rpr')),
                'rpr': safe_int(runner.get('rpr')),
                'timeform_rating': safe_int(runner.get('tfr')),
                'tsr': safe_int(runner.get('ts')),
                'comment': runner.get('comment'),  # Use comment field (spotlight doesn't exist in schema)
                'silk_url': runner.get('silk_url'),
                'api_data': runner,  # Store full runner API response
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            runner_records.append(runner_record)

        return race_record, runner_records


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("RACES REFERENCE DATA FETCHER")
    logger.info("=" * 60)

    fetcher = RacesFetcher()

    # Fetch last 30 days of UK and Irish races
    result = fetcher.fetch_and_store(
        days_back=30,
        region_codes=['gb', 'ire']
    )

    logger.info("\n" + "=" * 60)
    logger.info("FETCH COMPLETE")
    logger.info(f"Success: {result.get('success')}")
    logger.info(f"Races fetched: {result.get('races_fetched', 0)}")
    logger.info(f"Runners fetched: {result.get('runners_fetched', 0)}")
    logger.info(f"Races inserted: {result.get('races_inserted', 0)}")
    logger.info(f"Runners inserted: {result.get('runners_inserted', 0)}")
    logger.info(f"Days fetched: {result.get('days_fetched', 0)}")
    logger.info(f"Days with data: {result.get('days_with_data', 0)}")
    logger.info("=" * 60)

    return result


if __name__ == '__main__':
    main()
