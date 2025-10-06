#!/usr/bin/env python3
"""
Schema Mapping for Racing API Combined Data to ra_odds_historical Table

Maps combined Racing API data (racecards + results) to ra_odds_historical table schema.
Extracts real pre-race odds from bookmaker array and calculates derived fields.

Key Features:
1. Extracts min/max odds from real bookmaker odds array
2. Calculates SP-based returns (win, each-way, place)
3. Derives market position and favorite rankings
4. Uses ACTUAL pre-race odds instead of estimates
"""

from typing import Dict, Optional, List
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class SchemaMapper:
    """Maps Racing API combined data to ra_odds_historical table schema"""

    # Irish courses for country inference
    IRISH_COURSES = {
        'LEOPARDSTOWN', 'CURRAGH', 'FAIRYHOUSE', 'PUNCHESTOWN',
        'GALWAY', 'LISTOWEL', 'NAAS', 'CORK', 'TIPPERARY',
        'KILLARNEY', 'DOWNPATRICK', 'DUNDALK', 'GOWRAN PARK',
        'KILBEGGAN', 'ROSCOMMON', 'SLIGO', 'TRAMORE', 'WEXFORD',
        'CLONMEL', 'THURLES', 'BALLINROBE', 'BELLEWSTOWN',
        'LAYTOWN'
    }

    def __init__(self):
        """Initialize the schema mapper"""
        self.stats = {
            'mapped': 0,
            'skipped': 0,
            'errors': 0
        }

    def extract_odds_minmax(self, pre_race_odds: List[Dict]) -> Dict[str, Optional[float]]:
        """
        Extract min and max odds from bookmaker odds array

        Args:
            pre_race_odds: Array of bookmaker odds from racecard

        Returns:
            Dictionary with min and max odds
        """
        if not pre_race_odds:
            return {'min': None, 'max': None}

        valid_odds = []
        for bookmaker_odds in pre_race_odds:
            decimal_str = bookmaker_odds.get('decimal')
            # Skip withdrawn/unavailable odds (marked as '-')
            if decimal_str and decimal_str != '-':
                try:
                    decimal_val = float(decimal_str)
                    if decimal_val > 1.0:  # Valid odds must be > 1.0
                        valid_odds.append(decimal_val)
                except (ValueError, TypeError):
                    continue

        if not valid_odds:
            return {'min': None, 'max': None}

        return {
            'min': min(valid_odds),
            'max': max(valid_odds)
        }

    def calculate_forecasted_odds(self, pre_race_odds: List[Dict]) -> Optional[float]:
        """
        Calculate forecasted odds as the average of all bookmaker odds

        Args:
            pre_race_odds: Array of bookmaker odds from racecard

        Returns:
            Average odds or None
        """
        if not pre_race_odds:
            return None

        valid_odds = []
        for bookmaker_odds in pre_race_odds:
            decimal_str = bookmaker_odds.get('decimal')
            # Skip withdrawn/unavailable odds (marked as '-')
            if decimal_str and decimal_str != '-':
                try:
                    decimal_val = float(decimal_str)
                    if decimal_val > 1.0:
                        valid_odds.append(decimal_val)
                except (ValueError, TypeError):
                    continue

        if not valid_odds:
            return None

        return sum(valid_odds) / len(valid_odds)

    def parse_race_class(self, class_str: Optional[str]) -> Optional[int]:
        """
        Parse race class from API format to integer

        Args:
            class_str: Class string like "class_1", "class_6", "Class 3", etc.

        Returns:
            Integer class (1-7) or None
        """
        if not class_str:
            return None

        # Handle "class_1" format
        if isinstance(class_str, str):
            # Try to extract number from string
            match = re.search(r'\d+', class_str)
            if match:
                return int(match.group())

        return None

    def calculate_sp_favorite_position(self, all_runners: List[Dict], current_sp_dec: Optional[str]) -> Optional[int]:
        """
        Calculate favorite position based on SP

        Args:
            all_runners: List of all runners in race with their SP
            current_sp_dec: Current runner's SP decimal

        Returns:
            Favorite position (1 = favorite, 2 = second favorite, etc.)
        """
        if not current_sp_dec or not all_runners:
            return None

        try:
            current_sp = float(current_sp_dec)

            # Get all valid SPs
            sps = []
            for runner in all_runners:
                sp_dec = runner.get('sp_dec')
                if sp_dec:
                    try:
                        sps.append(float(sp_dec))
                    except (ValueError, TypeError):
                        pass

            if not sps:
                return None

            # Sort SPs (lowest = favorite)
            sorted_sps = sorted(set(sps))

            # Find position
            for idx, sp in enumerate(sorted_sps, 1):
                if current_sp == sp:
                    return idx

            return None

        except (ValueError, TypeError):
            return None

    def calculate_sp_win_return(self, sp_dec: Optional[str], position: Optional[str]) -> Optional[float]:
        """
        Calculate win return from SP

        Args:
            sp_dec: Starting Price in decimal format
            position: Finishing position

        Returns:
            Win return (profit per £1 stake, or 0 if lost)
        """
        if not sp_dec or not position:
            return None

        try:
            sp = float(sp_dec)

            # Check if won (position = "1")
            if str(position).strip() == "1":
                return sp  # Return includes stake
            else:
                return 0.0  # Lost - no return

        except (ValueError, TypeError):
            return None

    def calculate_ew_return(self, sp_dec: Optional[str], position: Optional[str],
                           runners_count: int = 0) -> Optional[float]:
        """
        Calculate each-way return based on SP and position

        Each-way rules (typical):
        - 5-7 runners: 1/4 odds, 2 places
        - 8-11 runners: 1/5 odds, 3 places
        - 12-15 runners: 1/4 odds, 3 places
        - 16+ runners: 1/4 odds, 4 places

        Args:
            sp_dec: Starting Price in decimal format
            position: Finishing position
            runners_count: Number of runners in race

        Returns:
            Each-way return or None
        """
        if not sp_dec or not position:
            return None

        try:
            sp = float(sp_dec)
            pos = int(position) if str(position).isdigit() else None

            if pos is None:
                return None

            # Determine place terms based on runners
            if runners_count >= 16:
                place_fraction = 0.25  # 1/4 odds
                place_positions = 4
            elif runners_count >= 12:
                place_fraction = 0.25
                place_positions = 3
            elif runners_count >= 8:
                place_fraction = 0.2  # 1/5 odds
                place_positions = 3
            elif runners_count >= 5:
                place_fraction = 0.25
                place_positions = 2
            else:
                return None  # No each-way betting

            # Calculate return
            if pos == 1:
                # Won: full win return + place return
                win_return = sp
                place_return = 1 + ((sp - 1) * place_fraction)
                return win_return + place_return  # Total EW return
            elif pos <= place_positions:
                # Placed: place return only
                place_return = 1 + ((sp - 1) * place_fraction)
                return place_return
            else:
                # Lost both
                return 0.0

        except (ValueError, TypeError):
            return None

    def calculate_place_return(self, sp_dec: Optional[str], position: Optional[str],
                              runners_count: int = 0) -> Optional[float]:
        """
        Calculate place-only return

        Args:
            sp_dec: Starting Price in decimal format
            position: Finishing position
            runners_count: Number of runners in race

        Returns:
            Place return or None
        """
        if not sp_dec or not position:
            return None

        try:
            sp = float(sp_dec)
            pos = int(position) if str(position).isdigit() else None

            if pos is None:
                return None

            # Determine place positions
            if runners_count >= 16:
                place_fraction = 0.25
                place_positions = 4
            elif runners_count >= 12:
                place_fraction = 0.25
                place_positions = 3
            elif runners_count >= 8:
                place_fraction = 0.2
                place_positions = 3
            elif runners_count >= 5:
                place_fraction = 0.25
                place_positions = 2
            else:
                return None

            # Calculate return
            if pos <= place_positions:
                return 1 + ((sp - 1) * place_fraction)
            else:
                return 0.0

        except (ValueError, TypeError):
            return None

    def map_combined_to_rb_odds(self, combined_data: Dict, all_runners: List[Dict] = None) -> Optional[Dict]:
        """
        Map a combined data record (racecards + results) to ra_odds_historical schema

        Args:
            combined_data: Combined data from historical_odds_fetcher (racecards + results joined)
            all_runners: All runners in the race (for calculating favorite position)

        Returns:
            Mapped record ready for insertion, or None if mapping fails
        """
        try:
            # Parse race class
            race_class = self.parse_race_class(combined_data.get('race_class'))

            # Calculate runners count
            runners_count = len(all_runners) if all_runners else 0

            # Get SP and position
            sp_dec = combined_data.get('sp_dec')
            position = combined_data.get('position')

            # Extract pre-race odds min/max from REAL bookmaker odds
            pre_race_odds = combined_data.get('pre_race_odds', [])
            odds_minmax = self.extract_odds_minmax(pre_race_odds)
            forecasted_odds = self.calculate_forecasted_odds(pre_race_odds)

            # Calculate derived fields
            sp_favorite_position = self.calculate_sp_favorite_position(all_runners or [], sp_dec)
            sp_win_return = self.calculate_sp_win_return(sp_dec, position)
            ew_return = self.calculate_ew_return(sp_dec, position, runners_count)
            place_return = self.calculate_place_return(sp_dec, position, runners_count)

            # Parse fields
            age = None
            if combined_data.get('age'):
                try:
                    age = int(combined_data.get('age'))
                except (ValueError, TypeError):
                    pass

            official_rating = None
            if combined_data.get('or'):
                try:
                    official_rating = int(combined_data.get('or'))
                except (ValueError, TypeError):
                    pass

            stall_number = None
            if combined_data.get('draw'):
                try:
                    stall_number = int(combined_data.get('draw'))
                except (ValueError, TypeError):
                    pass

            industry_sp = None
            if sp_dec:
                try:
                    industry_sp = float(sp_dec)
                except (ValueError, TypeError):
                    pass

            # Build mapped record
            mapped = {
                # Primary key (auto-generated)
                # 'racing_bet_data_id': auto-increment

                # Race identification
                'date_of_race': self._format_date(combined_data.get('race_date')),
                'country': 'IRE' if combined_data.get('region') == 'ire' else 'GB',
                'track': combined_data.get('course', '').upper() if combined_data.get('course') else None,
                'race_time': combined_data.get('off_time'),

                # Race details
                'going': combined_data.get('going'),
                'race_type': combined_data.get('race_type'),
                'distance': combined_data.get('distance'),
                'race_class': race_class,
                'runners_count': runners_count if runners_count > 0 else None,

                # Horse & participant information
                'horse_name': combined_data.get('horse_name'),
                'official_rating': official_rating,
                'age': age,
                'weight': combined_data.get('weight'),
                'jockey': combined_data.get('jockey'),
                'trainer': combined_data.get('trainer'),
                'headgear': combined_data.get('headgear'),
                'stall_number': stall_number,

                # Market position
                'sp_favorite_position': sp_favorite_position,

                # Odds data (Industry SP from Results API)
                'industry_sp': industry_sp,

                # Results
                'finishing_position': position,
                'winning_distance': combined_data.get('btn'),  # beaten by (lengths)

                # Pre-race odds (REAL data from bookmakers!)
                'ip_min': odds_minmax['min'],  # Actual minimum odds across all bookmakers
                'ip_max': odds_minmax['max'],  # Actual maximum odds across all bookmakers
                'pre_race_min': odds_minmax['min'],  # Same as ip_min
                'pre_race_max': odds_minmax['max'],  # Same as ip_max
                'forecasted_odds': forecasted_odds,  # Average of all bookmaker odds

                # Returns & performance (calculated)
                'sp_win_return': sp_win_return,
                'ew_return': ew_return,
                'place_return': place_return,

                # Metadata & tracking
                'data_source': 'Racing API - Racecards + Results',
                'file_source': 'racing_api_combined_v1',

                # Timestamps
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'match_timestamp': combined_data.get('off_dt'),
            }

            # Validate required fields
            required_fields = {'date_of_race', 'track', 'horse_name'}
            missing = required_fields - {k for k, v in mapped.items() if v is not None}

            if missing:
                logger.warning(f"Missing required fields: {missing}")
                self.stats['skipped'] += 1
                return None

            self.stats['mapped'] += 1
            return mapped

        except Exception as e:
            logger.error(f"Error mapping record: {e}")
            self.stats['errors'] += 1
            return None

    def _format_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Format date to ISO 8601 with timezone

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            ISO 8601 formatted date string
        """
        if not date_str:
            return None

        try:
            # Parse date and add timezone
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.strftime('%Y-%m-%dT00:00:00+00:00')
        except ValueError:
            # Already in ISO format or invalid
            return date_str

    def map_batch(self, combined_records: List[Dict]) -> List[Dict]:
        """
        Map multiple combined records

        Note: Groups records by race to calculate favorite positions correctly

        Args:
            combined_records: List of combined records from fetcher

        Returns:
            List of mapped records (excludes failed mappings)
        """
        mapped_records = []

        # Group by race_id to calculate favorite positions
        races = {}
        for record in combined_records:
            race_id = record.get('race_id')
            if race_id:
                if race_id not in races:
                    races[race_id] = []
                races[race_id].append(record)

        # Map each record with access to all runners in race
        for race_id, runners in races.items():
            for runner in runners:
                mapped = self.map_combined_to_rb_odds(runner, all_runners=runners)
                if mapped:
                    mapped_records.append(mapped)

        return mapped_records

    def print_mapping_stats(self):
        """Print mapping statistics"""
        print("\n" + "="*60)
        print("SCHEMA MAPPING STATISTICS")
        print("="*60)
        print(f"Successfully mapped:  {self.stats['mapped']:,}")
        print(f"Skipped:              {self.stats['skipped']:,}")
        print(f"Errors:               {self.stats['errors']:,}")

        total = sum(self.stats.values())
        if total > 0:
            success_rate = (self.stats['mapped'] / total) * 100
            print(f"Success rate:         {success_rate:.1f}%")

        print("="*60 + "\n")


if __name__ == "__main__":
    # Test the mapper
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    mapper = SchemaMapper()

    # Test record with pre-race odds
    test_record = {
        'race_id': 'rac_12345',
        'horse_id': 'hrs_67890',
        'race_date': '2024-09-30',
        'region': 'gb',
        'course': 'Ascot',
        'off_time': '14:30:00',
        'off_dt': '2024-09-30T14:30:00+01:00',
        'race_name': 'Test Stakes',
        'race_class': 'class_2',
        'race_type': 'flat',
        'distance': '1m',
        'going': 'good',
        'horse_name': 'Test Horse',
        'jockey': 'J Smith',
        'trainer': 'T Jones',
        'age': '4',
        'weight': '9-0',
        'draw': '5',
        'headgear': 'v',
        'position': '1',
        'btn': '0',
        'sp': '5/2',
        'sp_dec': '3.5',
        'or': '110',
        # Pre-race odds from multiple bookmakers
        'pre_race_odds': [
            {'bookmaker': 'Bet365', 'decimal': '3.25', 'fractional': '9/4'},
            {'bookmaker': 'William Hill', 'decimal': '3.5', 'fractional': '5/2'},
            {'bookmaker': 'Coral', 'decimal': '3.75', 'fractional': '11/4'},
            {'bookmaker': 'Ladbrokes', 'decimal': '3.4', 'fractional': '12/5'},
            {'bookmaker': 'Betfair', 'decimal': '3.6', 'fractional': '13/5'},
        ]
    }

    print("Testing Schema Mapper with Real Pre-Race Odds")
    print("="*60)

    mapped = mapper.map_combined_to_rb_odds(test_record, all_runners=[test_record])

    if mapped:
        print("\nMapped record:")
        print(f"  Horse: {mapped['horse_name']}")
        print(f"  SP: {mapped['industry_sp']}")
        print(f"  Pre-race min odds: {mapped['ip_min']}")
        print(f"  Pre-race max odds: {mapped['ip_max']}")
        print(f"  Forecasted odds: {mapped['forecasted_odds']}")
        print(f"  SP win return: {mapped['sp_win_return']}")
        print(f"  EW return: {mapped['ew_return']}")
        print(f"  Place return: {mapped['place_return']}")

    mapper.print_mapping_stats()
