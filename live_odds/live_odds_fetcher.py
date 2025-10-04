"""
Live Odds Fetcher Module
Fetches real-time odds from all available bookmakers via Racing API
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Bookmaker mappings from API response keys (module level for export)
BOOKMAKER_MAPPING = {
    # Exchanges
    'betfair': {'id': 'betfair', 'name': 'Betfair', 'type': 'exchange', 'display_name': 'Betfair'},
    'betfair_ex': {'id': 'betfair', 'name': 'Betfair', 'type': 'exchange', 'display_name': 'Betfair'},
    'smarkets': {'id': 'smarkets', 'name': 'Smarkets', 'type': 'exchange', 'display_name': 'Smarkets'},
    'matchbook': {'id': 'matchbook', 'name': 'Matchbook', 'type': 'exchange', 'display_name': 'Matchbook'},
    'betdaq': {'id': 'betdaq', 'name': 'Betdaq', 'type': 'exchange', 'display_name': 'Betdaq'},

    # Fixed odds bookmakers
    'bet365': {'id': 'bet365', 'name': 'Bet365', 'type': 'fixed', 'display_name': 'Bet365'},
    'williamhill': {'id': 'williamhill', 'name': 'William Hill', 'type': 'fixed', 'display_name': 'William Hill'},
    'will_hill': {'id': 'williamhill', 'name': 'William Hill', 'type': 'fixed', 'display_name': 'William Hill'},
    'paddypower': {'id': 'paddypower', 'name': 'Paddy Power', 'type': 'fixed', 'display_name': 'Paddy Power'},
    'paddy_power': {'id': 'paddypower', 'name': 'Paddy Power', 'type': 'fixed', 'display_name': 'Paddy Power'},
    'ladbrokes': {'id': 'ladbrokes', 'name': 'Ladbrokes', 'type': 'fixed', 'display_name': 'Ladbrokes'},
    'coral': {'id': 'coral', 'name': 'Coral', 'type': 'fixed', 'display_name': 'Coral'},
    'skybet': {'id': 'skybet', 'name': 'Sky Bet', 'type': 'fixed', 'display_name': 'Sky Bet'},
    'sky_bet': {'id': 'skybet', 'name': 'Sky Bet', 'type': 'fixed', 'display_name': 'Sky Bet'},
    'betfred': {'id': 'betfred', 'name': 'Betfred', 'type': 'fixed', 'display_name': 'Betfred'},
    'unibet': {'id': 'unibet', 'name': 'Unibet', 'type': 'fixed', 'display_name': 'Unibet'},
    'betvictor': {'id': 'betvictor', 'name': 'BetVictor', 'type': 'fixed', 'display_name': 'BetVictor'},
    'bet_victor': {'id': 'betvictor', 'name': 'BetVictor', 'type': 'fixed', 'display_name': 'BetVictor'},
    'betway': {'id': 'betway', 'name': 'Betway', 'type': 'fixed', 'display_name': 'Betway'},
    'boyle': {'id': 'boylesports', 'name': 'BoyleSports', 'type': 'fixed', 'display_name': 'BoyleSports'},
    'boylesports': {'id': 'boylesports', 'name': 'BoyleSports', 'type': 'fixed', 'display_name': 'BoyleSports'},
    '888sport': {'id': '888sport', 'name': '888 Sport', 'type': 'fixed', 'display_name': '888 Sport'},
    'sport888': {'id': '888sport', 'name': '888 Sport', 'type': 'fixed', 'display_name': '888 Sport'}
}


@dataclass
class OddsData:
    """Structure for odds data - FIXED ODDS ONLY (no exchange data available)"""
    race_id: str
    horse_id: str
    bookmaker_id: str
    bookmaker_name: str
    bookmaker_type: str
    odds_decimal: Optional[float] = None
    odds_fractional: Optional[str] = None
    market_status: str = 'OPEN'
    in_play: bool = False
    odds_timestamp: datetime = None


class LiveOddsFetcher:
    """Production-ready live odds fetcher for all bookmakers"""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize live odds fetcher"""
        self.config = config or {}

        # API Configuration
        self.base_url = "https://api.theracingapi.com/v1"
        self.username = os.getenv('RACING_API_USERNAME')
        self.password = os.getenv('RACING_API_PASSWORD')

        # Fetch Configuration
        self.hours_ahead = int(os.getenv('LIVE_HOURS_AHEAD', '4'))
        self.max_workers = int(os.getenv('LIVE_MAX_WORKERS', '5'))
        self.api_delay = float(os.getenv('LIVE_API_DELAY', '0.2'))

        # Session setup
        self.session = self._create_session()

        # Statistics
        self.stats = {
            'races_processed': 0,
            'horses_processed': 0,
            'bookmakers_found': set(),
            'odds_fetched': 0,
            'errors': 0,
            'start_time': None
        }

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic"""
        session = requests.Session()
        session.auth = (self.username, self.password)

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=30
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def fetch_upcoming_races(self) -> List[Dict]:
        """Fetch races happening in the next few hours"""
        logger.info(f"Fetching upcoming races for next {self.hours_ahead} hours")

        races = []
        now = datetime.now()
        end_time = now + timedelta(hours=self.hours_ahead)

        # Fetch today and tomorrow's races
        dates = [now.date(), (now + timedelta(days=1)).date()]

        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            day_races = self._fetch_races_for_date(date_str)

            # Filter races within our time window
            for race in day_races:
                off_dt_str = race.get('off_dt')
                if off_dt_str:
                    try:
                        off_dt = datetime.fromisoformat(off_dt_str.replace('Z', '+00:00'))
                        if now <= off_dt <= end_time:
                            races.append(race)
                    except:
                        pass

        logger.info(f"Found {len(races)} upcoming races")
        return races

    def _fetch_races_for_date(self, date: str) -> List[Dict]:
        """Fetch races for a specific date"""
        url = f"{self.base_url}/racecards/pro"
        params = [
            ('date', date),  # API expects 'date' not 'day'
            ('region_codes', 'gb'),
            ('region_codes', 'ire')
        ]

        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                # API returns 'racecards' not 'races'
                racecards = data.get('racecards', [])

                # Process racecards to extract race info with horses
                races = []
                for card in racecards:
                    race = {
                        'race_id': card.get('race_id'),
                        'course': card.get('course'),
                        'race_date': card.get('date'),
                        'off_time': card.get('off_time'),
                        'off_dt': card.get('off_dt'),
                        'race_name': card.get('race_name'),
                        'race_class': card.get('race_class'),
                        'race_type': card.get('type'),
                        'distance': card.get('distance'),
                        'going': card.get('going'),
                        'runners': card.get('runners', [])  # Contains horses
                    }
                    races.append(race)

                return races
            return []
        except Exception as e:
            logger.error(f"Error fetching races for {date}: {e}")
            self.stats['errors'] += 1
            return []

    def fetch_live_odds(self, race_id: str, horse_id: str) -> List[OddsData]:
        """
        DEPRECATED: This endpoint no longer works (returns 404)
        Use parse_embedded_odds() instead to get odds from racecards response
        """
        logger.warning(f"fetch_live_odds() is deprecated - odds should be parsed from racecards")
        return []

    def parse_embedded_odds(self, runner: Dict, race_id: str) -> List[OddsData]:
        """
        Parse odds from embedded pre_race_odds array in racecard runner data

        Args:
            runner: Runner dict from racecard response containing 'pre_race_odds'
            race_id: Race identifier

        Returns:
            List of OddsData objects, one per bookmaker
        """
        odds_list = []
        timestamp = datetime.now()
        horse_id = runner.get('horse_id', '')

        # Get embedded odds from racecard (field name is 'odds')
        embedded_odds = runner.get('odds', [])

        if not embedded_odds:
            logger.debug(f"No odds for {runner.get('horse')} in race {race_id}")
            return []

        # Parse each bookmaker's odds
        for bookie_data in embedded_odds:
            try:
                bookmaker_name = bookie_data.get('bookmaker', '')
                decimal_odds = bookie_data.get('decimal', '')
                fractional_odds = bookie_data.get('fractional', '')

                # Skip if withdrawn or SP only
                if decimal_odds in ['-', 'SP', ''] or not decimal_odds:
                    continue

                # Map bookmaker name to our internal ID
                bookmaker_key = bookmaker_name.lower().replace(' ', '')
                bookmaker_info = BOOKMAKER_MAPPING.get(bookmaker_key)

                if not bookmaker_info:
                    # Create default mapping for unmapped bookmakers
                    bookmaker_info = {
                        'id': bookmaker_key,
                        'name': bookmaker_name,
                        'type': 'fixed',
                        'display_name': bookmaker_name
                    }
                    logger.debug(f"Unmapped bookmaker: {bookmaker_name} -> {bookmaker_key}")

                # Create odds object
                odds = OddsData(
                    race_id=race_id,
                    horse_id=horse_id,
                    bookmaker_id=bookmaker_info['id'],
                    bookmaker_name=bookmaker_info['name'],
                    bookmaker_type=bookmaker_info['type'],
                    odds_decimal=float(decimal_odds) if decimal_odds else None,
                    odds_fractional=fractional_odds if fractional_odds else None,
                    odds_timestamp=timestamp
                )

                if odds.odds_decimal:
                    odds_list.append(odds)
                    self.stats['bookmakers_found'].add(bookmaker_info['id'])

            except Exception as e:
                logger.debug(f"Error parsing bookmaker odds: {e} - Data: {bookie_data}")
                continue

        return odds_list

    # NOTE: The methods below (_parse_odds_response, _parse_exchange_odds, _parse_fixed_odds)
    # are DEPRECATED and not used in production. They were designed for the old /odds/{race_id}/{horse_id}
    # endpoint which has been deprecated by Racing API. We now use parse_embedded_odds() to extract
    # odds directly from the racecard response. These methods are kept for reference only.

    def fetch_all_live_odds(self, races: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Parse live odds for all horses from racecards data (no additional API calls needed)

        Args:
            races: List of race dicts from fetch_upcoming_races() with runners data

        Returns:
            Tuple of (all_odds_records, stats)
        """
        logger.info(f"Parsing live odds from {len(races)} races")
        self.stats['start_time'] = datetime.now()

        all_odds = []

        # Process each race
        for race in races:
            race_id = race.get('race_id')
            if not race_id:
                continue

            race_meta = {
                'race_id': race_id,
                'race_date': race.get('race_date'),
                'race_time': race.get('off_time'),
                'off_dt': race.get('off_dt'),
                'course': race.get('course'),
                'race_name': race.get('race_name'),
                'race_class': race.get('race_class'),
                'race_type': race.get('race_type'),
                'distance': race.get('distance'),
                'going': race.get('going'),
                'runners': len(race.get('runners', []))
            }

            # Process each runner
            for runner in race.get('runners', []):
                horse_id = runner.get('horse_id')
                if not horse_id:
                    continue

                horse_meta = {
                    **race_meta,
                    'horse_id': horse_id,
                    'horse_name': runner.get('horse'),
                    'horse_number': runner.get('number'),
                    'jockey': runner.get('jockey'),
                    'trainer': runner.get('trainer'),
                    'draw': runner.get('draw'),
                    'weight': runner.get('weight'),
                    'age': runner.get('age'),
                    'form': runner.get('form')
                }

                # Parse embedded odds from this runner
                try:
                    odds_list = self.parse_embedded_odds(runner, race_id)

                    # Combine metadata with each bookmaker's odds
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
                        self.stats['odds_fetched'] += 1

                    self.stats['horses_processed'] += 1

                except Exception as e:
                    logger.error(f"Error processing odds for {runner.get('horse')}: {e}")
                    self.stats['errors'] += 1

            self.stats['races_processed'] += 1

            # Progress logging
            if self.stats['races_processed'] % 10 == 0:
                logger.info(f"Progress: {self.stats['races_processed']} races, {len(all_odds)} odds records")

        # Final statistics
        self.stats['duration_seconds'] = (datetime.now() - self.stats['start_time']).total_seconds()
        self.stats['bookmakers_found'] = list(self.stats['bookmakers_found'])
        self.stats['status'] = 'success' if self.stats['errors'] == 0 else 'completed_with_errors'

        logger.info(f"✅ Live odds parsing completed: {len(all_odds)} records from {len(self.stats['bookmakers_found'])} bookmakers")
        logger.info(f"   Races: {self.stats['races_processed']}, Horses: {self.stats['horses_processed']}, Duration: {self.stats['duration_seconds']:.2f}s")
        return all_odds, self.stats

    def close(self):
        """Clean up resources"""
        if self.session:
            self.session.close()