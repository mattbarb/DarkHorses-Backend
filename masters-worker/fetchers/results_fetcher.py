"""
Results Reference Data Fetcher
Fetches race results from Racing API results endpoint
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

logger = get_logger('results_fetcher')


class ResultsFetcher:
    """Fetcher for race results reference data"""

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
        days_back: int = 365,
        region_codes: List[str] = None
    ) -> Dict:
        """
        Fetch results from API and store in database

        Args:
            start_date: Start date (YYYY-MM-DD format). If None, calculated from days_back
            end_date: End date (YYYY-MM-DD format). If None, defaults to today
            days_back: Number of days to go back (default: 365 = ~12 months, API limit)
            region_codes: Optional list of region codes to filter (e.g., ['gb', 'ire'])

        Returns:
            Statistics dictionary
        """
        logger.info("Starting results fetch")
        logger.info(f"Region filtering: {region_codes if region_codes else 'None (all regions)'}")
        logger.warning("Note: Results API on Standard plan is limited to last 12 months")

        # Calculate date range
        if end_date is None:
            end_dt = datetime.utcnow().date()
        else:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

        if start_date is None:
            start_dt = end_dt - timedelta(days=days_back)
        else:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()

        # Warn if date range exceeds 12 months
        date_diff = (end_dt - start_dt).days
        if date_diff > 365:
            logger.warning(f"Date range ({date_diff} days) exceeds 12 months. API may limit results.")

        logger.info(f"Fetching results from {start_dt} to {end_dt}")

        all_results = []
        days_fetched = 0
        days_with_data = 0

        # Iterate day by day
        current_date = start_dt
        while current_date <= end_dt:
            date_str = current_date.strftime('%Y-%m-%d')
            logger.info(f"Fetching results for {date_str}")

            # Fetch results for this date
            api_response = self.api_client.get_results(
                date=date_str,
                region_codes=region_codes
            )

            if not api_response or 'results' not in api_response:
                logger.warning(f"No results returned for {date_str}")
                current_date += timedelta(days=1)
                days_fetched += 1
                continue

            results = api_response.get('results', [])
            if results:
                days_with_data += 1
                logger.info(f"Fetched {len(results)} results for {date_str}")

                # Transform and store results
                for result in results:
                    result_data = self._transform_result(result)
                    if result_data:
                        all_results.append(result_data)

            days_fetched += 1
            current_date += timedelta(days=1)

        logger.info(f"Total results fetched: {len(all_results)}")
        logger.info(f"Days fetched: {days_fetched}, Days with data: {days_with_data}")

        # Store in database
        results_dict = {}
        if all_results:
            result_stats = self.db_client.insert_results(all_results)
            results_dict['results'] = result_stats
            logger.info(f"Results inserted: {result_stats}")

        return {
            'success': True,
            'fetched': len(all_results),
            'inserted': results_dict.get('results', {}).get('inserted', 0),
            'days_fetched': days_fetched,
            'days_with_data': days_with_data,
            'api_stats': self.api_client.get_stats(),
            'db_stats': results_dict
        }

    def _transform_result(self, result: Dict) -> Optional[Dict]:
        """
        Transform API result data into database format

        Args:
            result: Raw result data from API

        Returns:
            Transformed result dictionary or None if invalid
        """
        race_id = result.get('id')
        if not race_id:
            logger.warning("Result missing race ID, skipping")
            return None

        # Build result record
        # Note: The exact structure depends on your ra_results table schema
        # This is a basic example - adjust fields as needed
        result_record = {
            'race_id': race_id,
            'course_id': result.get('course_id'),
            'course_name': result.get('course'),
            'race_name': result.get('race_name'),
            'race_date': result.get('race_date'),
            'off_datetime': result.get('off_dt'),
            'off_time': result.get('off_time'),
            'race_type': result.get('type'),
            'race_class': result.get('race_class'),
            'distance': result.get('distance'),
            'distance_f': result.get('distance_f'),
            'surface': result.get('surface'),
            'going': result.get('going'),
            'prize_money': result.get('prize'),
            'currency': result.get('currency'),
            'region': result.get('region'),
            'results_status': result.get('results_status'),
            'is_abandoned': result.get('is_abandoned', False),
            'api_data': result,  # Store full API response
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        # Extract finishing positions if available
        # The API results endpoint includes runner results with positions
        runners = result.get('runners', [])
        if runners:
            result_record['field_size'] = len(runners)
            # You might want to store runner results separately
            # in a ra_runner_results table - that's optional

        return result_record


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("RESULTS REFERENCE DATA FETCHER")
    logger.info("=" * 60)

    fetcher = ResultsFetcher()

    # Fetch last 365 days (12 months) of UK and Irish results
    # Note: Standard plan API limits to last 12 months
    result = fetcher.fetch_and_store(
        days_back=365,
        region_codes=['gb', 'ire']
    )

    logger.info("\n" + "=" * 60)
    logger.info("FETCH COMPLETE")
    logger.info(f"Success: {result.get('success')}")
    logger.info(f"Results fetched: {result.get('fetched', 0)}")
    logger.info(f"Results inserted: {result.get('inserted', 0)}")
    logger.info(f"Days fetched: {result.get('days_fetched', 0)}")
    logger.info(f"Days with data: {result.get('days_with_data', 0)}")
    logger.info("=" * 60)

    return result


if __name__ == '__main__':
    main()
