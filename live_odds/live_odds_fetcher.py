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
    """Structure for odds data"""
    race_id: str
    horse_id: str
    bookmaker_id: str
    bookmaker_name: str
    bookmaker_type: str
    odds_decimal: Optional[float] = None
    odds_fractional: Optional[str] = None
    back_price: Optional[float] = None
    lay_price: Optional[float] = None
    back_size: Optional[float] = None
    lay_size: Optional[float] = None
    back_prices: Optional[List] = None
    lay_prices: Optional[List] = None
    total_matched: Optional[float] = None
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
        """Fetch live odds for a specific horse from all bookmakers"""
        url = f"{self.base_url}/odds/{race_id}/{horse_id}"

        try:
            time.sleep(self.api_delay)
            response = self.session.get(url, timeout=30)  # Increased from 10 to 30 seconds

            if response.status_code == 200:
                data = response.json()
                logger.debug(f"   📥 API Response for {horse_id}: {data}")
                odds_list = self._parse_odds_response(data, race_id, horse_id)
                if not odds_list:
                    logger.warning(f"   ⚠️  API returned data but no odds parsed for {race_id}/{horse_id}. Response keys: {list(data.keys())}")
                return odds_list
            elif response.status_code == 404:
                logger.debug(f"   404 - No odds available for {race_id}/{horse_id}")
                return []  # No odds available
            else:
                logger.warning(f"   ⚠️  API returned {response.status_code} for {race_id}/{horse_id}")
                logger.warning(f"   Response: {response.text[:200]}")
                return []

        except Exception as e:
            logger.error(f"   ❌ Error fetching live odds for {race_id}/{horse_id}: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            self.stats['errors'] += 1
            return []

    def _parse_odds_response(self, data: Dict, race_id: str, horse_id: str) -> List[OddsData]:
        """Parse API response and extract odds from all bookmakers"""
        odds_list = []
        timestamp = datetime.now()

        # Handle exchange odds (Betfair, Smarkets, etc.)
        if 'exchange' in data:
            for exchange_key, exchange_data in data['exchange'].items():
                if exchange_data and isinstance(exchange_data, dict):
                    bookmaker_info = BOOKMAKER_MAPPING.get(exchange_key.lower())
                    if bookmaker_info:
                        odds = self._parse_exchange_odds(
                            exchange_data, race_id, horse_id,
                            bookmaker_info, timestamp
                        )
                        if odds:
                            odds_list.append(odds)
                            self.stats['bookmakers_found'].add(bookmaker_info['id'])

        # Handle fixed odds bookmakers
        if 'bookmakers' in data:
            for bookie_key, bookie_data in data['bookmakers'].items():
                if bookie_data:
                    bookmaker_info = BOOKMAKER_MAPPING.get(bookie_key.lower())
                    if bookmaker_info:
                        odds = self._parse_fixed_odds(
                            bookie_data, race_id, horse_id,
                            bookmaker_info, timestamp
                        )
                        if odds:
                            odds_list.append(odds)
                            self.stats['bookmakers_found'].add(bookmaker_info['id'])

        # Also check for 'odds' key (Racing API format)
        if 'odds' in data:
            odds_data = data['odds']
            logger.debug(f"   📊 'odds' key found. Type: {type(odds_data)}")

            # Handle array format (Racing API live odds)
            if isinstance(odds_data, list):
                logger.info(f"   📋 Processing {len(odds_data)} bookmakers from odds array")
                for bookmaker_odds in odds_data:
                    if not isinstance(bookmaker_odds, dict):
                        continue

                    bookmaker_name = bookmaker_odds.get('bookmaker', '').lower()
                    # Map bookmaker name to our internal format
                    bookmaker_key = bookmaker_name.replace(' ', '').replace('sports', '').replace('bet', '')
                    bookmaker_info = BOOKMAKER_MAPPING.get(bookmaker_key.lower())

                    # If not found, try the original name
                    if not bookmaker_info:
                        bookmaker_info = BOOKMAKER_MAPPING.get(bookmaker_name)

                    if bookmaker_info:
                        # Parse decimal odds, skip if unavailable ('-' or None)
                        decimal_value = bookmaker_odds.get('decimal')
                        if decimal_value and decimal_value != '-':
                            try:
                                decimal_float = float(decimal_value)
                            except (ValueError, TypeError):
                                logger.debug(f"   ⚠️  Invalid decimal value for {bookmaker_name}: {decimal_value}")
                                continue
                        else:
                            # Skip odds that are withdrawn/unavailable
                            logger.debug(f"   ⏭️  Skipping {bookmaker_name} - odds withdrawn/unavailable")
                            continue

                        # Create OddsData object
                        odds = OddsData(
                            race_id=race_id,
                            horse_id=horse_id,
                            bookmaker_id=bookmaker_info['id'],
                            bookmaker_name=bookmaker_info['display_name'],
                            bookmaker_type=bookmaker_info['type'],
                            odds_decimal=decimal_float,
                            odds_fractional=bookmaker_odds.get('fractional'),
                            odds_timestamp=timestamp
                        )
                        odds_list.append(odds)
                        self.stats['bookmakers_found'].add(bookmaker_info['id'])
                        logger.debug(f"   ✅ Added {bookmaker_info['display_name']}: {odds.odds_decimal}")
                    else:
                        logger.debug(f"   ⚠️  Unknown bookmaker: {bookmaker_name}")

            # Handle dict format (legacy/other APIs)
            elif isinstance(odds_data, dict):
                logger.debug(f"   🔑 Keys in odds dict: {list(odds_data.keys())}")
                for key, value in odds_data.items():
                    logger.debug(f"   🔍 Processing odds key '{key}': {value}")
                    bookmaker_info = BOOKMAKER_MAPPING.get(key.lower())
                    if bookmaker_info and value:
                        if bookmaker_info['type'] == 'exchange':
                            odds = self._parse_exchange_odds(
                                value, race_id, horse_id,
                                bookmaker_info, timestamp
                            )
                        else:
                            odds = self._parse_fixed_odds(
                                value, race_id, horse_id,
                                bookmaker_info, timestamp
                            )
                        if odds:
                            odds_list.append(odds)
                            self.stats['bookmakers_found'].add(bookmaker_info['id'])

        return odds_list

    def _parse_exchange_odds(self, data: Dict, race_id: str, horse_id: str,
                            bookmaker_info: Dict, timestamp: datetime) -> Optional[OddsData]:
        """Parse exchange odds data"""
        try:
            odds = OddsData(
                race_id=race_id,
                horse_id=horse_id,
                bookmaker_id=bookmaker_info['id'],
                bookmaker_name=bookmaker_info['name'],
                bookmaker_type='exchange',
                odds_timestamp=timestamp
            )

            # Extract back/lay prices
            if 'back' in data:
                back_data = data['back']
                if isinstance(back_data, list) and len(back_data) > 0:
                    odds.back_price = float(back_data[0].get('price', 0))
                    odds.back_size = float(back_data[0].get('size', 0))
                    odds.back_prices = back_data[:3]  # Top 3 prices
                elif isinstance(back_data, dict):
                    odds.back_price = float(back_data.get('price', 0))
                    odds.back_size = float(back_data.get('size', 0))

            if 'lay' in data:
                lay_data = data['lay']
                if isinstance(lay_data, list) and len(lay_data) > 0:
                    odds.lay_price = float(lay_data[0].get('price', 0))
                    odds.lay_size = float(lay_data[0].get('size', 0))
                    odds.lay_prices = lay_data[:3]  # Top 3 prices
                elif isinstance(lay_data, dict):
                    odds.lay_price = float(lay_data.get('price', 0))
                    odds.lay_size = float(lay_data.get('size', 0))

            # Total matched amount
            if 'matched' in data:
                odds.total_matched = float(data['matched'])

            # Market status
            if 'status' in data:
                odds.market_status = data['status'].upper()
            if 'in_play' in data:
                odds.in_play = bool(data['in_play'])

            return odds if (odds.back_price or odds.lay_price) else None

        except Exception as e:
            logger.error(f"Error parsing exchange odds: {e}")
            return None

    def _parse_fixed_odds(self, data: Any, race_id: str, horse_id: str,
                         bookmaker_info: Dict, timestamp: datetime) -> Optional[OddsData]:
        """Parse fixed odds bookmaker data"""
        try:
            odds = OddsData(
                race_id=race_id,
                horse_id=horse_id,
                bookmaker_id=bookmaker_info['id'],
                bookmaker_name=bookmaker_info['name'],
                bookmaker_type='fixed',
                odds_timestamp=timestamp
            )

            # Handle different data formats
            if isinstance(data, (int, float)):
                odds.odds_decimal = float(data)
            elif isinstance(data, str):
                # Could be fractional odds like "5/1"
                odds.odds_fractional = data
                odds.odds_decimal = self._fractional_to_decimal(data)
            elif isinstance(data, dict):
                # Complex odds object
                if 'decimal' in data:
                    odds.odds_decimal = float(data['decimal'])
                elif 'price' in data:
                    odds.odds_decimal = float(data['price'])
                if 'fractional' in data:
                    odds.odds_fractional = data['fractional']

            return odds if odds.odds_decimal else None

        except Exception as e:
            logger.error(f"Error parsing fixed odds: {e}")
            return None

    def _fractional_to_decimal(self, fractional: str) -> Optional[float]:
        """Convert fractional odds to decimal"""
        try:
            if '/' in fractional:
                num, denom = fractional.split('/')
                return 1 + (float(num) / float(denom))
            return None
        except:
            return None

    def fetch_all_live_odds(self, races: List[Dict]) -> Tuple[List[Dict], Dict]:
        """Fetch live odds for all horses in given races"""
        logger.info(f"Fetching live odds for {len(races)} races")
        self.stats['start_time'] = datetime.now()

        all_odds = []
        combinations = []

        # Extract all horse/race combinations
        for race in races:
            race_id = race.get('id_race')
            if not race_id:
                continue

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

            for horse in race.get('horses', []):
                horse_id = horse.get('id_horse')
                if not horse_id:
                    continue

                combination = {
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
                combinations.append(combination)

        self.stats['races_processed'] = len(races)
        self.stats['horses_processed'] = len(combinations)

        # Fetch odds in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_combo = {
                executor.submit(
                    self.fetch_live_odds,
                    combo['race_id'],
                    combo['horse_id']
                ): combo
                for combo in combinations
            }

            for future in as_completed(future_to_combo):
                combo = future_to_combo[future]
                try:
                    odds_list = future.result()
                    # Combine metadata with each odds record
                    for odds in odds_list:
                        record = {
                            **combo,
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

                except Exception as e:
                    logger.error(f"Error processing odds: {e}")
                    self.stats['errors'] += 1

                # Progress logging
                if len(all_odds) % 100 == 0:
                    logger.info(f"Progress: {len(all_odds)} odds records fetched")

        # Final statistics
        self.stats['duration_seconds'] = (datetime.now() - self.stats['start_time']).total_seconds()
        self.stats['bookmakers_found'] = list(self.stats['bookmakers_found'])
        self.stats['status'] = 'success' if self.stats['errors'] == 0 else 'completed_with_errors'

        logger.info(f"Live odds fetch completed: {len(all_odds)} records from {len(self.stats['bookmakers_found'])} bookmakers")
        return all_odds, self.stats

    def close(self):
        """Clean up resources"""
        if self.session:
            self.session.close()