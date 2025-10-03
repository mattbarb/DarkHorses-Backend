#!/usr/bin/env python3
"""
Historical Odds Fetcher
Fetches completed race data with final odds from Racing API
Captures odds at race start time from all bookmakers
"""

import os
import logging
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
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
    """Fetches historical odds data from Racing API"""

    def __init__(self, rate_limit_delay: float = 0.3):
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
            'User-Agent': 'HistoricalOddsFetcher/1.0',
            'Accept': 'application/json'
        })

        self.stats = {
            'total_races': 0,
            'total_horses': 0,
            'total_odds': 0,
            'api_calls': 0,
            'errors': 0
        }

    def get_completed_races(self, date: str, regions: List[str] = ['gb', 'ire']) -> List[Dict]:
        """
        Get completed races for a specific date using /racecards/pro endpoint

        Args:
            date: Date in YYYY-MM-DD format
            regions: List of region codes (default: UK and Ireland)

        Returns:
            List of race dictionaries with results
        """
        all_races = []

        # Use separate API calls for each region (API format requirement)
        for region in regions:
            try:
                url = f"{self.base_url}/racecards/pro"

                # Build params list (API expects repeated region_codes params)
                params = [
                    ('date', date),  # API expects 'date' parameter for racecards
                    ('region_codes', region)
                ]

                time.sleep(self.rate_limit_delay)
                response = self.session.get(url, params=params, timeout=30)
                self.stats['api_calls'] += 1

                if response.status_code == 200:
                    data = response.json()

                    # Handle racecards response format
                    racecards = data.get('racecards', [])
                    region_race_count = 0

                    # Process racecards - each card IS a race
                    for card in racecards:
                        # Each racecard IS the race data
                        all_races.append(card)
                        region_race_count += 1

                    logger.info(f"Found {region_race_count} {region.upper()} races for {date}")

                elif response.status_code == 404:
                    logger.info(f"No {region.upper()} races found for {date}")

                elif response.status_code == 429:
                    logger.warning(f"Rate limited, waiting 5 seconds...")
                    time.sleep(5)
                    # Retry once
                    response = self.session.get(url, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, dict) and 'results' in data:
                            races = data['results']
                        elif isinstance(data, list):
                            races = data
                        else:
                            races = []
                        all_races.extend(races)

                else:
                    logger.error(f"Error fetching {region} races: {response.status_code}")
                    self.stats['errors'] += 1

            except Exception as e:
                logger.error(f"Exception fetching {region} races for {date}: {e}")
                self.stats['errors'] += 1

        self.stats['total_races'] += len(all_races)
        return all_races

    def get_race_odds(self, race_id: str, horse_id: str) -> Optional[Dict]:
        """
        Get odds for a specific race/horse combination

        Args:
            race_id: Race identifier
            horse_id: Horse identifier

        Returns:
            Odds data dictionary or None
        """
        try:
            url = f"{self.base_url}/odds/{race_id}/{horse_id}"

            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, timeout=10)
            self.stats['api_calls'] += 1

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # No odds available - not an error
                return None
            elif response.status_code == 429:
                logger.warning(f"Rate limited on odds fetch, waiting 3 seconds...")
                time.sleep(3)
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    return response.json()
                return None
            else:
                logger.debug(f"Odds fetch failed: {response.status_code} for {race_id}/{horse_id}")
                return None

        except Exception as e:
            logger.debug(f"Exception fetching odds for {race_id}/{horse_id}: {e}")
            return None

    def extract_odds_from_response(self, odds_response: Dict, race_data: Dict,
                                   horse_data: Dict) -> List[Dict]:
        """
        Extract individual bookmaker odds from API response

        Args:
            odds_response: Raw odds API response
            race_data: Race metadata
            horse_data: Horse metadata

        Returns:
            List of normalized odds records (one per bookmaker)
        """
        odds_records = []

        # Get bookmaker odds from response
        # The API returns odds as a list in the 'odds' field
        bookmakers = odds_response.get('odds', [])

        for bookmaker in bookmakers:
            try:
                # Extract bookmaker info from the correct fields
                bookmaker_name = bookmaker.get('bookmaker', 'Unknown')
                bookmaker_id = bookmaker_name.lower().replace(' ', '_').replace('-', '_')

                # Get odds values (they're strings in the API response)
                odds_decimal_str = bookmaker.get('decimal')
                odds_fractional = bookmaker.get('fractional')

                # Convert decimal odds to float
                try:
                    odds_decimal = float(odds_decimal_str) if odds_decimal_str else None
                except (ValueError, TypeError):
                    odds_decimal = None

                # Skip if no valid odds
                if not odds_decimal or odds_decimal <= 1:
                    continue

                # Build normalized record
                record = {
                    'race_id': race_data['race_id'],
                    'horse_id': horse_data['horse_id'],
                    'bookmaker_id': bookmaker_id,
                    'race_date': race_data['race_date'],
                    'course': race_data['course'],
                    'off_time': race_data.get('off_time'),
                    'off_dt': race_data.get('off_dt'),
                    'race_name': race_data.get('race_name'),
                    'race_class': race_data.get('race_class'),
                    'race_type': race_data.get('race_type'),
                    'distance': race_data.get('distance'),
                    'distance_f': race_data.get('distance_f'),
                    'going': race_data.get('going'),
                    'prize_money': race_data.get('prize'),
                    'num_runners': len(race_data.get('runners', [])),
                    'horse_name': horse_data['horse_name'],
                    'jockey': horse_data.get('jockey'),
                    'jockey_id': horse_data.get('jockey_id'),
                    'trainer': horse_data.get('trainer'),
                    'trainer_id': horse_data.get('trainer_id'),
                    'draw': horse_data.get('draw'),
                    'weight': horse_data.get('weight'),
                    'age': horse_data.get('age'),
                    'form': horse_data.get('form'),
                    'sp': horse_data.get('sp'),
                    'sp_decimal': horse_data.get('sp_dec'),
                    'position': horse_data.get('position'),
                    'distance_behind': horse_data.get('distance_behind'),
                    'official_result': horse_data.get('official_result'),
                    'bookmaker_name': bookmaker_name,
                    'odds_decimal': odds_decimal,
                    'odds_fractional': odds_fractional,
                    'fetched_at': datetime.now().isoformat()
                }

                odds_records.append(record)
                self.stats['total_odds'] += 1

            except Exception as e:
                logger.error(f"Error extracting bookmaker odds: {e}")
                continue

        return odds_records

    def fetch_date_odds(self, date: str, regions: List[str] = ['gb', 'ire'], limit_for_test: int = None) -> List[Dict]:
        """
        Fetch all odds for a specific date

        Args:
            date: Date in YYYY-MM-DD format
            regions: List of region codes
            limit_for_test: Limit number of races for testing (None = all races)

        Returns:
            List of all odds records for the date
        """
        logger.info(f"Fetching historical odds for {date}...")

        # Get completed races
        races = self.get_completed_races(date, regions)

        if not races:
            logger.warning(f"No races found for {date}")
            return []

        logger.info(f"Found {len(races)} completed races for {date}")

        # Limit races for testing
        if limit_for_test:
            races = races[:limit_for_test]
            logger.info(f"Limited to {len(races)} races for testing")

        all_odds = []
        self.stats['total_races'] = len(races)

        for i, race in enumerate(races):

            race_id = race.get('race_id')
            if not race_id:
                # Try alternative field names
                race_id = race.get('id') or race.get('race_id_uk')
                if not race_id:
                    logger.warning(f"No race_id found for race at {race.get('course', 'unknown')}")
                    continue

            # Extract race metadata
            race_data = {
                'race_id': race_id,
                'race_date': date,
                'course': race.get('course', 'Unknown'),
                'off_time': race.get('off_time'),
                'off_dt': race.get('off_dt'),
                'race_name': race.get('race_name'),
                'race_class': race.get('race_class'),
                'race_type': race.get('race_type'),
                'distance': race.get('distance'),
                'distance_f': race.get('distance_f'),
                'going': race.get('going'),
                'prize': race.get('prize'),
                'runners': race.get('runners', [])
            }

            # Process each horse in the race
            runners = race.get('runners', [])
            self.stats['total_horses'] += len(runners)

            for runner in runners:
                horse_id = runner.get('horse_id')
                if not horse_id:
                    continue

                # Extract horse metadata
                horse_data = {
                    'horse_id': horse_id,
                    'horse_name': runner.get('horse', 'Unknown'),
                    'jockey': runner.get('jockey'),
                    'jockey_id': runner.get('jockey_id'),
                    'trainer': runner.get('trainer'),
                    'trainer_id': runner.get('trainer_id'),
                    'draw': runner.get('draw'),
                    'weight': runner.get('weight'),
                    'age': runner.get('age'),
                    'form': runner.get('form'),
                    'sp': runner.get('sp'),
                    'sp_dec': runner.get('sp_dec'),
                    'position': runner.get('position'),
                    'distance_behind': runner.get('distance_behind'),
                    'official_result': runner.get('official_result')
                }

                # Fetch odds for this horse
                odds_response = self.get_race_odds(race_id, horse_id)

                if odds_response:
                    # Extract odds from all bookmakers
                    odds_records = self.extract_odds_from_response(
                        odds_response, race_data, horse_data
                    )
                    all_odds.extend(odds_records)

        logger.info(f"Fetched {len(all_odds)} odds records for {date}")
        return all_odds

    def fetch_date_range(self, start_date: str, end_date: str,
                        regions: List[str] = ['gb', 'ire']) -> List[Dict]:
        """
        Fetch odds for a date range

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            regions: List of region codes

        Returns:
            List of all odds records in range
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        all_odds = []
        current = start

        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            date_odds = self.fetch_date_odds(date_str, regions)
            all_odds.extend(date_odds)
            current += timedelta(days=1)

        return all_odds

    def print_stats(self):
        """Print fetching statistics"""
        print("\n" + "="*60)
        print("FETCHING STATISTICS")
        print("="*60)
        print(f"Total races:      {self.stats['total_races']:,}")
        print(f"Total horses:     {self.stats['total_horses']:,}")
        print(f"Total odds:       {self.stats['total_odds']:,}")
        print(f"API calls:        {self.stats['api_calls']:,}")
        print(f"Errors:           {self.stats['errors']:,}")
        print("="*60 + "\n")


if __name__ == "__main__":
    # Test the fetcher
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Test with yesterday's date
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"Testing Historical Odds Fetcher")
    print(f"Fetching data for: {yesterday}")
    print("="*60)

    fetcher = HistoricalOddsFetcher()

    # Fetch odds for yesterday
    odds = fetcher.fetch_date_odds(yesterday)

    print(f"\nFetched {len(odds)} odds records")
    fetcher.print_stats()

    if odds:
        print("\nSample record:")
        print(odds[0])