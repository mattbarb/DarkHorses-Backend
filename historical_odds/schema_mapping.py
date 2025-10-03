#!/usr/bin/env python3
"""
Schema Mapping for Racing API to rb_odds_historical Table

Maps Racing API data structure to the existing rb_odds_historical table schema.
The existing table is Betfair-focused with columns like betfair_sp, industry_sp, etc.
We need to map Racing API bookmaker odds appropriately.

Key Mapping Decisions:
1. Racing API provides odds from multiple bookmakers
2. We'll store individual bookmaker odds in relevant columns
3. Use 'industry_sp' for bookmaker odds (as it represents industry pricing)
4. Track data source to distinguish Racing API from Betfair data
5. Match records by: date_of_race + track + race_time + horse_name
6. Map course names to course_ids from ra_courses table
"""

from typing import Dict, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SchemaMapper:
    """Maps Racing API data to rb_odds_historical table schema"""

    # Column mapping from Racing API to rb_odds_historical
    COLUMN_MAPPING = {
        # Primary identification fields
        'race_date': 'date_of_race',
        'course': 'track',
        'off_time': 'race_time',
        'horse_name': 'horse_name',

        # Race metadata
        'race_class': 'race_class',
        'race_type': 'race_type',
        'distance': 'distance',
        'going': 'going',

        # Horse/Participant data
        'jockey': 'jockey',
        'trainer': 'trainer',
        'age': 'age',
        'weight': 'weight',
        'draw': 'stall_number',

        # Result data
        'position': 'finishing_position',
        'distance_behind': 'winning_distance',
        'sp': 'industry_sp',  # Starting price from Racing API
        'sp_decimal': 'industry_sp',  # Use decimal format

        # Bookmaker odds - map to industry_sp
        'odds_decimal': 'industry_sp',  # Primary mapping for bookmaker odds
    }

    # Fields that exist in Racing API but not in rb_odds_historical
    # We'll store these in metadata or skip them
    UNMAPPED_FIELDS = [
        'race_id',        # Racing API identifier (not in existing table)
        'horse_id',       # Racing API identifier (not in existing table)
        'bookmaker_id',   # We'll use this to identify source
        'bookmaker_name', # We'll store in data_source
        'off_dt',         # Full datetime (we use race_time)
        'race_name',      # Not in existing schema
        'jockey_id',      # IDs not in existing schema
        'trainer_id',
        'form',           # Not in existing schema
        'odds_fractional', # We use decimal
        'prize_money',    # Not in existing schema
        'num_runners',    # Available as runners_count
        'distance_f',     # Distance in furlongs (we have distance)
        'official_result' # We have finishing_position
    ]

    # Required fields in rb_odds_historical that must have values
    # In the new clean table, only racing_bet_data_id, created_at, updated_at are NOT NULL
    # But for data quality, we require these essential fields
    REQUIRED_FIELDS = {
        'date_of_race',
        'track',
        'horse_name'
    }

    def __init__(self):
        """Initialize the schema mapper"""
        self.stats = {
            'mapped': 0,
            'skipped': 0,
            'errors': 0
        }

    def map_racing_api_to_rb_odds(self, racing_api_record: Dict) -> Optional[Dict]:
        """
        Map a single Racing API record to rb_odds_historical schema

        Args:
            racing_api_record: Record from Racing API with bookmaker odds

        Returns:
            Mapped record ready for insertion, or None if mapping fails
        """
        try:
            mapped = {}

            # Map basic fields using column mapping
            for api_field, db_field in self.COLUMN_MAPPING.items():
                if api_field in racing_api_record:
                    value = racing_api_record[api_field]

                    # Special handling for certain fields
                    if db_field == 'industry_sp':
                        # Convert to float, handle multiple sources
                        if api_field == 'odds_decimal':
                            mapped['industry_sp'] = float(value) if value else None
                        elif api_field in ['sp', 'sp_decimal'] and 'industry_sp' not in mapped:
                            mapped['industry_sp'] = float(value) if value else None

                    elif db_field == 'date_of_race':
                        # Ensure proper date format (ISO 8601 with timezone)
                        if isinstance(value, str):
                            # API provides YYYY-MM-DD, convert to ISO 8601
                            try:
                                dt = datetime.strptime(value, '%Y-%m-%d')
                                mapped['date_of_race'] = dt.strftime('%Y-%m-%dT00:00:00+00:00')
                            except:
                                mapped['date_of_race'] = value

                    elif db_field == 'track':
                        # Uppercase track names to match existing data
                        mapped['track'] = value.upper() if value else None

                    elif db_field == 'finishing_position':
                        # Ensure string format for position
                        mapped['finishing_position'] = str(value) if value else None

                    elif db_field == 'stall_number':
                        # Draw/stall number
                        mapped['stall_number'] = int(value) if value else None

                    elif db_field == 'race_class':
                        # Extract numeric class from strings like "Class 6" or just "6"
                        if isinstance(value, str):
                            # Try to extract number from string
                            import re
                            match = re.search(r'\d+', value)
                            if match:
                                mapped['race_class'] = int(match.group())
                            else:
                                mapped['race_class'] = None
                        elif value is not None:
                            try:
                                mapped['race_class'] = int(value)
                            except (ValueError, TypeError):
                                mapped['race_class'] = None
                        else:
                            mapped['race_class'] = None

                    else:
                        mapped[db_field] = value

            # Set country based on course location (infer from data or default)
            # In a real system, you'd have a lookup table
            # For now, default to GB (can be enhanced)
            mapped['country'] = self._infer_country(racing_api_record.get('course', ''))

            # Note: darkhorses_course_id column has been removed
            # The new table structure does not use foreign key references to ra_courses

            # In the new clean table, all fields except ID and timestamps are nullable
            # No need to set default values, but we can for data quality if desired
            # The application logic should handle missing values appropriately

            # Note: darkhorses columns (darkhorses_race_id, darkhorses_jockey_id, darkhorses_runner_id,
            # darkhorses_course_id) have been removed from the new table structure

            # Set data source to track origin
            bookmaker_name = racing_api_record.get('bookmaker_name', 'Racing API')
            mapped['data_source'] = f'Racing API - {bookmaker_name}'

            # Add file source tracking
            mapped['file_source'] = 'racing_api_automated'

            # Set timestamps
            now = datetime.now().isoformat()
            mapped['created_at'] = now
            mapped['updated_at'] = now
            mapped['match_timestamp'] = now

            # Set default values for Betfair-specific fields that aren't available
            # These will be NULL unless we have data
            betfair_fields = {
                'betfair_sp': None,
                'betfair_win_return': None,
                'betfair_lay_return': None,
                'betfair_place_sp': None,
                'betfair_rank': None,
                'placed_in_betfair_market': None,
                'ip_min': None,
                'ip_max': None,
                'pre_race_min': None,
                'pre_race_max': None,
                'forecasted_odds': None,
                'sp_win_return': None,
                'ew_return': None,
                'place_return': None,
                'place_lay_return': None,
                'tick_reduction': None,
                'tick_inflation': None,
                'bsp_reduction_percent': None,
                'bsp_inflation_percent': None,
            }

            # Only add betfair fields if they don't already exist
            for field, default_value in betfair_fields.items():
                if field not in mapped:
                    mapped[field] = default_value

            # Validate required fields
            missing = self.REQUIRED_FIELDS - set(mapped.keys())
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

    def _infer_country(self, course_name: str) -> str:
        """
        Infer country from course name

        Args:
            course_name: Name of the course/track

        Returns:
            'GB' or 'IRE'
        """
        if not course_name:
            return 'GB'  # Default

        course_name = course_name.upper()

        # Irish courses (not exhaustive, add more as needed)
        irish_courses = {
            'LEOPARDSTOWN', 'CURRAGH', 'FAIRYHOUSE', 'PUNCHESTOWN',
            'GALWAY', 'LISTOWEL', 'NAAS', 'CORK', 'TIPPERARY',
            'KILLARNEY', 'DOWNPATRICK', 'DUNDALK', 'GOWRAN PARK',
            'KILBEGGAN', 'ROSCOMMON', 'SLIGO', 'TRAMORE', 'WEXFORD',
            'CLONMEL', 'THURLES', 'BALLINROBE', 'BELLEWSTOWN',
            'LAYTOWN'
        }

        return 'IRE' if course_name in irish_courses else 'GB'

    def map_batch(self, racing_api_records: List[Dict]) -> List[Dict]:
        """
        Map multiple Racing API records

        Args:
            racing_api_records: List of Racing API records

        Returns:
            List of mapped records (excludes failed mappings)
        """
        mapped_records = []

        for record in racing_api_records:
            mapped = self.map_racing_api_to_rb_odds(record)
            if mapped:
                mapped_records.append(mapped)

        return mapped_records

    def create_unique_key(self, record: Dict) -> str:
        """
        Create a unique key for duplicate detection

        Key: date + track + time + horse_name

        Args:
            record: Mapped record

        Returns:
            Unique key string
        """
        date = record.get('date_of_race', '')
        track = record.get('track', '')
        time = record.get('race_time', '')
        horse = record.get('horse_name', '')

        # Extract just the date part if it's a full timestamp
        if 'T' in date:
            date = date.split('T')[0]

        return f"{date}|{track}|{time}|{horse}"

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

    def get_column_definitions(self) -> Dict[str, str]:
        """
        Get column definitions for reference

        Returns:
            Dictionary of column names and their purposes
        """
        return {
            'racing_bet_data_id': 'Auto-increment primary key',
            'date_of_race': 'Race date (ISO 8601 format)',
            'country': 'GB or IRE',
            'track': 'Track/course name (uppercase)',
            'going': 'Track conditions',
            'race_type': 'Race type (Flat, NH, etc)',
            'distance': 'Race distance',
            'race_class': 'Race classification',
            'race_time': 'Race start time (HH:MM:SS)',
            'horse_name': 'Horse name',
            'official_rating': 'Official rating',
            'age': 'Horse age',
            'weight': 'Weight carried',
            'jockey': 'Jockey name',
            'trainer': 'Trainer name',
            'headgear': 'Headgear worn',
            'stall_number': 'Starting stall/draw',
            'sp_favorite_position': 'SP favorite ranking',
            'runners_count': 'Number of runners',
            'industry_sp': 'Starting price (decimal)',
            'betfair_sp': 'Betfair starting price',
            'finishing_position': 'Final position',
            'winning_distance': 'Distance behind winner',
            'data_source': 'Data source identifier',
            'file_source': 'Source file identifier',
            'created_at': 'Record creation timestamp',
            'updated_at': 'Record update timestamp',
        }


if __name__ == "__main__":
    # Test the mapper
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    mapper = SchemaMapper()

    # Test record from Racing API
    test_record = {
        'race_id': 'rac_12345',
        'horse_id': 'hrs_67890',
        'bookmaker_id': 'bet365',
        'race_date': '2024-09-30',
        'course': 'Ascot',
        'off_time': '14:30:00',
        'race_class': 2,
        'race_type': 'Flat',
        'distance': '1m',
        'going': 'Good',
        'horse_name': 'Test Horse',
        'jockey': 'J Smith',
        'trainer': 'T Jones',
        'age': 4,
        'weight': '9-0',
        'draw': 5,
        'position': '1',
        'sp': '5.0',
        'sp_decimal': 5.0,
        'bookmaker_name': 'Bet365',
        'odds_decimal': 4.5,
        'odds_fractional': '7/2'
    }

    print("Testing Schema Mapper")
    print("="*60)

    mapped = mapper.map_racing_api_to_rb_odds(test_record)

    if mapped:
        print("\nOriginal Racing API Record:")
        for key, value in test_record.items():
            print(f"  {key}: {value}")

        print("\nMapped to rb_odds_historical:")
        for key, value in mapped.items():
            print(f"  {key}: {value}")

        print("\nUnique Key:", mapper.create_unique_key(mapped))

    mapper.print_mapping_stats()