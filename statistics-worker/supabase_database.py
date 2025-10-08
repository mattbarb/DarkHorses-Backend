"""
Supabase-based database connection for statistics queries

This replaces the direct PostgreSQL connection (database.py) to work from any network.
Uses Supabase SDK which is accessible from anywhere, unlike direct db.*.supabase.co connections.
"""
import logging
import os
from typing import List, Dict, Optional
from supabase import create_client, Client

logger = logging.getLogger('STATISTICS_SUPABASE')


class SupabaseDatabase:
    """Manages Supabase connections for statistics queries using SDK"""

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize Supabase client

        Args:
            supabase_url: Supabase project URL (or use SUPABASE_URL env var)
            supabase_key: Supabase service key (or use SUPABASE_SERVICE_KEY env var)
        """
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_SERVICE_KEY')

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("✅ Supabase client initialized (works from any network)")

    def connect(self):
        """No-op for compatibility with DatabaseConnection interface"""
        return self.client

    def disconnect(self):
        """No-op for compatibility with DatabaseConnection interface"""
        pass

    def execute_scalar(self, query: str, params: tuple = None) -> any:
        """
        Execute SQL query and return single scalar value

        Note: For complex queries, uses Supabase PostgREST .rpc() method
        """
        # Parse simple aggregate queries and use Supabase SDK
        query_lower = query.lower().strip()

        # Extract table name
        if 'from ra_odds_live' in query_lower:
            table = 'ra_odds_live'
        elif 'from ra_odds_historical' in query_lower:
            table = 'ra_odds_historical'
        else:
            raise ValueError(f"Unsupported query: {query}")

        # COUNT(*) queries with time intervals (NOW() - INTERVAL)
        if query_lower.startswith('select count(*)'):
            import re
            from datetime import datetime, timedelta

            query_builder = self.client.table(table).select('*', count='exact')

            # Handle WHERE created_at >= NOW() - INTERVAL 'X hour/day/days'
            interval_match = re.search(r"created_at >= now\(\) - interval '(\d+) (hour|day|days)'", query_lower)
            if interval_match:
                amount = int(interval_match.group(1))
                unit = interval_match.group(2)

                if unit == 'hour':
                    cutoff = datetime.utcnow() - timedelta(hours=amount)
                elif unit in ['day', 'days']:
                    cutoff = datetime.utcnow() - timedelta(days=amount)
                else:
                    cutoff = datetime.utcnow()

                query_builder = query_builder.gte('created_at', cutoff.isoformat())

            response = query_builder.limit(1).execute()
            return response.count

        # COUNT(DISTINCT column) queries
        elif 'count(distinct' in query_lower:
            # Extract column name
            import re
            match = re.search(r'count\(distinct\s+(\w+)\)', query_lower)
            if match:
                column = match.group(1)
                # Fetch all unique values for this column
                response = self.client.table(table).select(column).execute()
                if response.data:
                    unique_values = set(row[column] for row in response.data if row.get(column) is not None)
                    return len(unique_values)
                return 0

        # MIN/MAX queries
        elif query_lower.startswith('select min('):
            import re
            match = re.search(r'min\((\w+)\)', query_lower)
            if match:
                column = match.group(1)
                response = self.client.table(table).select(column).order(column, desc=False).limit(1).execute()
                if response.data:
                    return response.data[0].get(column)
                return None

        elif query_lower.startswith('select max('):
            import re
            match = re.search(r'max\((\w+)\)', query_lower)
            if match:
                column = match.group(1)
                response = self.client.table(table).select(column).order(column, desc=True).limit(1).execute()
                if response.data:
                    return response.data[0].get(column)
                return None

        else:
            raise ValueError(f"Query pattern not supported by Supabase adapter: {query[:100]}...")

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Execute SQL query and return results as list of dicts

        For complex GROUP BY queries, fetches all data and aggregates in Python
        """
        query_lower = query.lower().strip()

        # Extract table name
        if 'from ra_odds_live' in query_lower:
            table = 'ra_odds_live'
        elif 'from ra_odds_historical' in query_lower:
            table = 'ra_odds_historical'
        else:
            raise ValueError(f"Unsupported query: {query}")

        # For GROUP BY or FILTER queries, fetch all data and aggregate in Python
        if 'group by' in query_lower or 'filter' in query_lower:
            return self._execute_aggregation_query(query, table)
        else:
            raise ValueError(f"Query pattern not supported: {query[:100]}...")

    def _execute_aggregation_query(self, query: str, table: str) -> List[Dict]:
        """
        Execute aggregation query by fetching data and aggregating in Python

        Handles queries like:
        - Bookmaker coverage (GROUP BY bookmaker_id)
        - Records per date (GROUP BY race_date)
        - Course distribution (GROUP BY course)
        - Market status (GROUP BY market_status)
        """
        query_lower = query.lower()

        # Determine which columns to fetch
        columns_to_fetch = '*'

        # Apply WHERE conditions
        query_builder = self.client.table(table).select(columns_to_fetch)

        # Parse WHERE clause
        if 'where' in query_lower:
            # Extract WHERE conditions
            import re

            # Handle race_date >= CURRENT_DATE
            if 'race_date >= current_date' in query_lower:
                from datetime import date
                today = date.today().isoformat()
                query_builder = query_builder.gte('race_date', today)

            # Handle race_date >= CURRENT_DATE - INTERVAL 'X days'
            interval_match = re.search(r"race_date >= current_date - interval '(\d+) days'", query_lower)
            if interval_match:
                from datetime import date, timedelta
                days = int(interval_match.group(1))
                cutoff = (date.today() - timedelta(days=days)).isoformat()
                query_builder = query_builder.gte('race_date', cutoff)

            # Handle IS NOT NULL
            if 'where course is not null' in query_lower:
                query_builder = query_builder.not_.is_('course', 'null')

        # Execute query to fetch all matching records
        logger.info(f"📍 Fetching data from {table} for aggregation...")
        response = query_builder.execute()

        if not response.data:
            logger.warning(f"No data returned from {table}")
            return []

        logger.info(f"✅ Fetched {len(response.data)} records, aggregating in Python...")

        # Aggregate in Python based on GROUP BY clause
        return self._aggregate_in_python(query, response.data)

    def _aggregate_in_python(self, query: str, data: List[Dict]) -> List[Dict]:
        """Aggregate data in Python to replicate SQL GROUP BY"""
        from collections import defaultdict
        from datetime import datetime

        query_lower = query.lower()

        # Bookmaker coverage query
        if 'group by bookmaker_id' in query_lower and 'bookmaker_name' in query_lower:
            groups = defaultdict(lambda: {
                'odds_count': 0,
                'races': set(),
                'horses': set(),
                'latest_odds': None
            })

            for row in data:
                key = row.get('bookmaker_id')
                if key:
                    groups[key]['bookmaker_id'] = key
                    groups[key]['bookmaker_name'] = row.get('bookmaker_name')
                    groups[key]['bookmaker_type'] = row.get('bookmaker_type')
                    groups[key]['odds_count'] += 1
                    groups[key]['races'].add(row.get('race_id'))
                    groups[key]['horses'].add(row.get('horse_id'))

                    odds_ts = row.get('odds_timestamp')
                    if odds_ts and (groups[key]['latest_odds'] is None or odds_ts > groups[key]['latest_odds']):
                        groups[key]['latest_odds'] = odds_ts

            result = []
            for group in groups.values():
                result.append({
                    'bookmaker_id': group['bookmaker_id'],
                    'bookmaker_name': group['bookmaker_name'],
                    'bookmaker_type': group['bookmaker_type'],
                    'odds_count': group['odds_count'],
                    'races_covered': len(group['races']),
                    'horses_covered': len(group['horses']),
                    'latest_odds': group['latest_odds']
                })

            # Sort by odds_count DESC
            result.sort(key=lambda x: x['odds_count'], reverse=True)
            return result

        # Records per date query (handles both race_date and DATE(date_of_race))
        elif 'group by race_date' in query_lower or 'group by date(date_of_race)' in query_lower:
            groups = defaultdict(lambda: {
                'record_count': 0,
                'races': set(),
                'bookmakers': set()
            })

            # Determine which date field to use
            date_field = 'date_of_race' if 'date_of_race' in query_lower else 'race_date'

            for row in data:
                key = row.get(date_field)
                if key:
                    # Convert to date string if needed
                    if isinstance(key, str):
                        key = key.split('T')[0]  # Extract date part
                    elif hasattr(key, 'isoformat'):
                        key = key.isoformat().split('T')[0]

                    groups[key]['race_date'] = key
                    groups[key]['record_count'] += 1
                    if row.get('race_id'):
                        groups[key]['races'].add(row.get('race_id'))
                    if row.get('bookmaker_id'):
                        groups[key]['bookmakers'].add(row.get('bookmaker_id'))

            result = []
            for group in groups.values():
                result.append({
                    'race_date': group['race_date'],
                    'record_count': group['record_count'],
                    'unique_races': len(group['races']) if group['races'] else 0,
                    'unique_bookmakers': len(group['bookmakers']) if group['bookmakers'] else 0
                })

            # Sort by race_date DESC
            result.sort(key=lambda x: x['race_date'], reverse=True)
            return result

        # Course distribution query
        elif 'group by course' in query_lower:
            groups = defaultdict(lambda: {
                'record_count': 0,
                'races': set(),
                'bookmakers': set()
            })

            for row in data:
                key = row.get('course')
                if key:
                    groups[key]['course'] = key
                    groups[key]['record_count'] += 1
                    groups[key]['races'].add(row.get('race_id'))
                    groups[key]['bookmakers'].add(row.get('bookmaker_id'))

            result = []
            for group in groups.values():
                result.append({
                    'course': group['course'],
                    'record_count': group['record_count'],
                    'unique_races': len(group['races']),
                    'unique_bookmakers': len(group['bookmakers'])
                })

            # Sort by record_count DESC
            result.sort(key=lambda x: x['record_count'], reverse=True)

            # Apply LIMIT if in query
            import re
            limit_match = re.search(r'limit (\d+)', query_lower)
            if limit_match:
                limit = int(limit_match.group(1))
                result = result[:limit]

            return result

        # Country distribution query (with percentage calculation)
        elif 'group by country' in query_lower:
            groups = defaultdict(int)
            total = len(data)

            for row in data:
                key = row.get('country')
                if key is not None:
                    groups[key] += 1

            result = []
            for country, count in groups.items():
                result.append({
                    'country': country,
                    'record_count': count,
                    'percentage': round(100.0 * count / total, 2) if total > 0 else 0
                })

            # Sort by record_count DESC
            result.sort(key=lambda x: x['record_count'], reverse=True)

            # Apply LIMIT if in query
            import re
            limit_match = re.search(r'limit (\d+)', query_lower)
            if limit_match:
                limit = int(limit_match.group(1))
                result = result[:limit]

            return result

        # Track distribution query
        elif 'group by track' in query_lower:
            groups = defaultdict(int)

            for row in data:
                key = row.get('track')
                if key is not None:
                    groups[key] += 1

            result = []
            for track, count in groups.items():
                result.append({
                    'track': track,
                    'record_count': count
                })

            # Sort by record_count DESC
            result.sort(key=lambda x: x['record_count'], reverse=True)

            # Apply LIMIT if in query
            import re
            limit_match = re.search(r'limit (\d+)', query_lower)
            if limit_match:
                limit = int(limit_match.group(1))
                result = result[:limit]

            return result

        # Market status query
        elif 'group by market_status' in query_lower:
            groups = defaultdict(int)
            total = len(data)

            for row in data:
                key = row.get('market_status')
                groups[key] += 1

            result = []
            for market_status, count in groups.items():
                result.append({
                    'market_status': market_status,
                    'record_count': count,
                    'percentage': round(100.0 * count / total, 2) if total > 0 else 0
                })

            # Sort by record_count DESC
            result.sort(key=lambda x: x['record_count'], reverse=True)
            return result

        # Data quality query (COUNT(*) FILTER) - supports both live and historical tables
        elif 'filter' in query_lower:
            result = {
                'total_records': len(data)
            }

            # Live odds table columns
            if any(col in query_lower for col in ['null_race_id', 'null_horse_id', 'null_bookmaker_id', 'null_odds_decimal']):
                result.update({
                    'null_race_id': sum(1 for row in data if row.get('race_id') is None),
                    'null_horse_id': sum(1 for row in data if row.get('horse_id') is None),
                    'null_bookmaker_id': sum(1 for row in data if row.get('bookmaker_id') is None),
                    'null_race_date': sum(1 for row in data if row.get('race_date') is None),
                    'null_course': sum(1 for row in data if row.get('course') is None),
                    'null_horse_name': sum(1 for row in data if row.get('horse_name') is None),
                    'null_odds_decimal': sum(1 for row in data if row.get('odds_decimal') is None),
                    'null_odds_timestamp': sum(1 for row in data if row.get('odds_timestamp') is None),
                })

            # Historical odds table columns
            if any(col in query_lower for col in ['null_date_of_race', 'null_track', 'null_industry_sp', 'null_finishing_position']):
                result.update({
                    'null_date_of_race': sum(1 for row in data if row.get('date_of_race') is None),
                    'null_track': sum(1 for row in data if row.get('track') is None),
                    'null_horse_name': sum(1 for row in data if row.get('horse_name') is None),
                    'null_industry_sp': sum(1 for row in data if row.get('industry_sp') is None),
                    'null_finishing_position': sum(1 for row in data if row.get('finishing_position') is None),
                    'null_jockey': sum(1 for row in data if row.get('jockey') is None),
                    'null_trainer': sum(1 for row in data if row.get('trainer') is None),
                    'null_country': sum(1 for row in data if row.get('country') is None),
                })

            # Odds coverage metrics (historical)
            if any(col in query_lower for col in ['has_industry_sp', 'has_pre_race_min', 'has_forecasted_odds']):
                result.update({
                    'has_industry_sp': sum(1 for row in data if row.get('industry_sp') is not None),
                    'has_pre_race_min': sum(1 for row in data if row.get('pre_race_min') is not None),
                    'has_pre_race_max': sum(1 for row in data if row.get('pre_race_max') is not None),
                    'has_forecasted_odds': sum(1 for row in data if row.get('forecasted_odds') is not None),
                })

            return [result]

        else:
            raise ValueError(f"Aggregation pattern not supported: {query[:100]}...")

    def test_connection(self) -> bool:
        """Test Supabase connectivity"""
        try:
            # Try a simple query
            response = self.client.table('ra_odds_live').select('id').limit(1).execute()
            logger.info("✅ Supabase connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ Supabase connection test failed: {e}")
            return False
