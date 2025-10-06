#!/usr/bin/env python3
"""
Historical Odds & Results Fetcher - Dual Endpoint Strategy
Fetches BOTH pre-race odds (/v1/racecards/pro) AND race results (/v1/results)
Combines them to get complete historical data with real pre-race bookmaker odds

Data Availability:
- Racecards: From 2023-01-23 onwards (when tracking began)
- Results: Last 12 months only
- Combined: Intersection of both (last 12 months, starting from 2023-01-23)
"""

import os
import logging
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables - optional for Render.com
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    # Running on Render.com - use system environment variables
    pass

logger = logging.getLogger(__name__)


class HistoricalOddsFetcher:
    """Fetches historical race results + pre-race odds from Racing API dual endpoints"""

    def __init__(self, rate_limit_delay: float = 0.5):
        """Initialize the fetcher with Racing API credentials"""
        self.username = os.getenv('RACING_API_USERNAME')
        self.password = os.getenv('RACING_API_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("RACING_API_USERNAME and RACING_API_PASSWORD must be set in .env")

        self.base_url = "https://api.theracingapi.com/v1"
        self.rate_limit_delay = rate_limit_delay

        # Setup session with auth
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({
            'User-Agent': 'HistoricalOddsFetcher/3.0-Dual',
            'Accept': 'application/json'
        })

        self.stats = {
            'total_races': 0,
            'total_runners': 0,
            'total_results': 0,
            'racecards_fetched': 0,
            'results_fetched': 0,
            'joined_records': 0,
            'api_calls': 0,
            'errors': 0
        }

    def get_racecards(self, date: str, regions: List[str] = ['gb', 'ire']) -> List[Dict]:
        """
        Get racecards for a specific date using /v1/racecards/pro endpoint

        Available from: 2023-01-23 onwards

        Args:
            date: Date in YYYY-MM-DD format
            regions: List of region codes (default: UK and Ireland)

        Returns:
            List of racecard dictionaries with pre-race odds
        """
        all_racecards = []

        for region in regions:
            try:
                url = f"{self.base_url}/racecards/pro"

                params = {
                    'date': date,
                    'region_codes': region
                }

                time.sleep(self.rate_limit_delay)
                response = self.session.get(url, params=params, timeout=30)
                self.stats['api_calls'] += 1

                if response.status_code == 200:
                    data = response.json()
                    racecards = data.get('racecards', [])
                    all_racecards.extend(racecards)
                    logger.info(f"Found {len(racecards)} {region.upper()} racecards for {date}")

                elif response.status_code == 404:
                    logger.info(f"No {region.upper()} racecards found for {date}")

                elif response.status_code == 429:
                    logger.warning(f"Rate limited, waiting 5 seconds...")
                    time.sleep(5)
                    continue

                else:
                    logger.error(f"Error fetching racecards: {response.status_code}")
                    self.stats['errors'] += 1

            except Exception as e:
                logger.error(f"Exception fetching racecards for {date} {region}: {e}")
                self.stats['errors'] += 1

        self.stats['racecards_fetched'] += len(all_racecards)
        return all_racecards

    def get_race_results(self, date: str, regions: List[str] = ['gb', 'ire']) -> List[Dict]:
        """
        Get race results for a specific date using /v1/results endpoint

        Available: Last 12 months only

        Args:
            date: Date in YYYY-MM-DD format
            regions: List of region codes (default: UK and Ireland)

        Returns:
            List of race result dictionaries with SP and positions
        """
        all_results = []

        try:
            url = f"{self.base_url}/results"

            params = {
                'start_date': date,
                'end_date': date,
                'region': regions,
                'limit': 50,
                'skip': 0
            }

            # Fetch all pages for this date
            while True:
                time.sleep(self.rate_limit_delay)
                response = self.session.get(url, params=params, timeout=30)
                self.stats['api_calls'] += 1

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])

                    if not results:
                        break

                    all_results.extend(results)

                    if len(results) < params['limit']:
                        break

                    params['skip'] += params['limit']

                elif response.status_code == 404:
                    logger.info(f"No results found for {date}")
                    break

                elif response.status_code == 429:
                    logger.warning(f"Rate limited, waiting 5 seconds...")
                    time.sleep(5)
                    continue

                else:
                    logger.error(f"Error fetching results: {response.status_code}")
                    self.stats['errors'] += 1
                    break

            logger.info(f"Found {len(all_results)} race results for {date}")
            self.stats['results_fetched'] += len(all_results)

            return all_results

        except Exception as e:
            logger.error(f"Exception fetching results for {date}: {e}")
            self.stats['errors'] += 1
            return []

    def join_racecards_and_results(self, racecards: List[Dict], results: List[Dict]) -> List[Dict]:
        """
        Join racecards and results data on race_id and horse_id

        Creates combined records with:
        - Pre-race odds from racecards
        - SP and outcomes from results

        Args:
            racecards: List of racecard objects from /v1/racecards/pro
            results: List of result objects from /v1/results

        Returns:
            List of joined runner records (one per horse)
        """
        joined_records = []

        # Build lookup dictionaries for fast joining
        # Results lookup: results_by_race[race_id] = result_object
        results_by_race = {r['race_id']: r for r in results}

        # Process each racecard
        for racecard in racecards:
            race_id = racecard.get('race_id')

            if not race_id:
                logger.warning(f"Racecard missing race_id: {racecard.get('race_name', 'unknown')}")
                continue

            # Find matching result
            matching_result = results_by_race.get(race_id)

            if not matching_result:
                logger.debug(f"No matching result for race_id: {race_id}")
                continue

            # Build result runner lookup
            result_runners_by_horse = {
                r['horse_id']: r for r in matching_result.get('runners', [])
            }

            # Process each runner in racecard
            for racecard_runner in racecard.get('runners', []):
                horse_id = racecard_runner.get('horse_id')

                if not horse_id:
                    continue

                # Find matching result runner
                result_runner = result_runners_by_horse.get(horse_id)

                if not result_runner:
                    logger.debug(f"No matching result for horse_id: {horse_id} in race {race_id}")
                    continue

                # Create joined record
                joined_record = {
                    # Race metadata (from result - more complete)
                    'race_id': race_id,
                    'race_date': matching_result.get('date'),
                    'region': matching_result.get('region'),
                    'course': matching_result.get('course'),
                    'course_id': matching_result.get('course_id'),
                    'off_time': matching_result.get('off'),
                    'off_dt': matching_result.get('off_dt'),
                    'race_name': matching_result.get('race_name'),
                    'race_type': matching_result.get('type'),
                    'race_class': matching_result.get('class'),
                    'pattern': matching_result.get('pattern'),
                    'distance': matching_result.get('dist'),
                    'distance_f': matching_result.get('dist_f'),
                    'going': matching_result.get('going'),
                    'surface': matching_result.get('surface'),
                    'winning_time': matching_result.get('winning_time_detail'),

                    # Tote data (from result)
                    'tote_win': matching_result.get('tote_win'),
                    'tote_pl': matching_result.get('tote_pl'),
                    'tote_ex': matching_result.get('tote_ex'),
                    'tote_csf': matching_result.get('tote_csf'),

                    # Horse identification
                    'horse_id': horse_id,
                    'horse_name': result_runner.get('horse'),

                    # Runner details (from result - has final data)
                    'jockey': result_runner.get('jockey'),
                    'jockey_id': result_runner.get('jockey_id'),
                    'trainer': result_runner.get('trainer'),
                    'trainer_id': result_runner.get('trainer_id'),
                    'age': result_runner.get('age'),
                    'weight': result_runner.get('weight'),
                    'draw': result_runner.get('draw'),
                    'headgear': result_runner.get('headgear'),

                    # Ratings (from result)
                    'or': result_runner.get('or'),
                    'rpr': result_runner.get('rpr'),
                    'tsr': result_runner.get('tsr'),

                    # Race result (from result)
                    'position': result_runner.get('position'),
                    'btn': result_runner.get('btn'),
                    'ovr_btn': result_runner.get('ovr_btn'),
                    'time': result_runner.get('time'),
                    'prize': result_runner.get('prize'),

                    # Starting Price (from result) - CRITICAL
                    'sp': result_runner.get('sp'),
                    'sp_dec': result_runner.get('sp_dec'),

                    # PRE-RACE ODDS (from racecard) - NEW!
                    'pre_race_odds': racecard_runner.get('odds', []),  # Array of bookmaker odds

                    # Additional racecard data
                    'form': racecard_runner.get('form'),
                    'racecard_comment': racecard_runner.get('comment'),

                    # Metadata
                    'fetched_at': datetime.now().isoformat()
                }

                joined_records.append(joined_record)
                self.stats['joined_records'] += 1

        logger.info(f"Joined {len(joined_records)} runner records from racecards and results")
        return joined_records

    def fetch_complete_date_data(self, date: str, regions: List[str] = ['gb', 'ire']) -> List[Dict]:
        """
        Fetch complete data for a date: racecards + results + join them

        This is the main method to use for fetching historical data.

        Args:
            date: Date in YYYY-MM-DD format (must be within last 12 months and after 2023-01-23)
            regions: List of region codes

        Returns:
            List of complete runner records with pre-race odds and results
        """
        logger.info(f"Fetching complete data for {date}...")

        # Step 1: Fetch racecards (pre-race odds)
        logger.info(f"  [1/3] Fetching racecards...")
        racecards = self.get_racecards(date, regions)

        if not racecards:
            logger.warning(f"No racecards found for {date}")
            return []

        # Step 2: Fetch results (SP and outcomes)
        logger.info(f"  [2/3] Fetching race results...")
        results = self.get_race_results(date, regions)

        if not results:
            logger.warning(f"No results found for {date}")
            return []

        # Step 3: Join them together
        logger.info(f"  [3/3] Joining racecards and results...")
        complete_data = self.join_racecards_and_results(racecards, results)

        logger.info(f"✅ Complete: {len(complete_data)} runner records with pre-race odds + results")
        return complete_data

    def fetch_date_range(self, start_date: str, end_date: str,
                        regions: List[str] = ['gb', 'ire']) -> List[Dict]:
        """
        Fetch complete data for a date range

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            regions: List of region codes

        Returns:
            List of all runner records in range
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        all_data = []
        current = start

        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            date_data = self.fetch_complete_date_data(date_str, regions)
            all_data.extend(date_data)
            current += timedelta(days=1)

        return all_data

    def print_stats(self):
        """Print fetching statistics"""
        print("\n" + "="*60)
        print("DUAL-ENDPOINT FETCHING STATISTICS")
        print("="*60)
        print(f"Racecards fetched: {self.stats['racecards_fetched']:,}")
        print(f"Results fetched:   {self.stats['results_fetched']:,}")
        print(f"Joined records:    {self.stats['joined_records']:,}")
        print(f"API calls:         {self.stats['api_calls']:,}")
        print(f"Errors:            {self.stats['errors']:,}")

        if self.stats['racecards_fetched'] > 0 and self.stats['results_fetched'] > 0:
            join_rate = (self.stats['joined_records'] /
                        max(self.stats['racecards_fetched'], self.stats['results_fetched'])) * 100
            print(f"Join success rate: {join_rate:.1f}%")

        print("="*60 + "\n")


if __name__ == "__main__":
    # Test the fetcher
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Test with yesterday's date (must be within last 12 months)
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"Testing Dual-Endpoint Historical Fetcher")
    print(f"Fetching data for: {yesterday}")
    print("="*60)

    fetcher = HistoricalOddsFetcher()

    # Fetch complete data (racecards + results)
    data = fetcher.fetch_complete_date_data(yesterday)

    print(f"\nFetched {len(data)} complete runner records")
    fetcher.print_stats()

    if data:
        print("\nSample complete record:")
        sample = data[0]
        print(f"Race: {sample.get('race_name')} at {sample.get('course')}")
        print(f"Horse: {sample.get('horse_name')}")
        print(f"Position: {sample.get('position')}")
        print(f"SP: {sample.get('sp')} ({sample.get('sp_dec')} decimal)")
        print(f"\nPre-race odds from {len(sample.get('pre_race_odds', []))} bookmakers:")
        for odds in sample.get('pre_race_odds', [])[:5]:  # Show first 5
            print(f"  {odds.get('bookmaker')}: {odds.get('fractional')} ({odds.get('decimal')})")
