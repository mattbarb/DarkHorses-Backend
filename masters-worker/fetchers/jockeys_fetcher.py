"""
Jockeys Reference Data Fetcher
Fetches jockey profiles from Racing API
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime
from typing import Dict
from config.config import get_config
from utils.logger import get_logger
from utils.api_client import RacingAPIClient
from utils.supabase_client import SupabaseReferenceClient
from utils.regional_filter import RegionalFilter

logger = get_logger('jockeys_fetcher')


class JockeysFetcher:
    """Fetcher for jockey reference data"""

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

    def fetch_and_store(self, limit_per_page: int = 500, max_pages: int = None,
                        filter_uk_ireland: bool = True) -> Dict:
        """
        Fetch jockeys from API and store in database

        Args:
            limit_per_page: Number of jockeys per page
            max_pages: Maximum pages to fetch (None = all)
            filter_uk_ireland: Filter to UK and Ireland jockeys only (default: True)
                             Note: API doesn't provide region data for jockeys,
                             so this currently includes all jockeys.
                             Future enhancement: filter based on race participation.

        Returns:
            Statistics dictionary
        """
        logger.info("Starting jockeys fetch")
        if filter_uk_ireland:
            logger.warning("UK/Ireland filtering requested but not available for jockeys API endpoint")
            logger.warning("Fetching all jockeys - consider implementing activity-based filtering")

        all_jockeys = []
        page = 0
        skip = 0

        while True:
            if max_pages and page >= max_pages:
                logger.info(f"Reached max pages limit ({max_pages})")
                break

            # Fetch page
            logger.info(f"Fetching page {page + 1} (skip={skip})")
            api_response = self.api_client.search_jockeys(limit=limit_per_page, skip=skip)

            if not api_response or 'jockeys' not in api_response:
                logger.warning(f"No jockeys returned for page {page + 1}")
                break

            jockeys_page = api_response.get('jockeys', [])
            if not jockeys_page:
                logger.info("No more jockeys to fetch")
                break

            all_jockeys.extend(jockeys_page)
            logger.info(f"Fetched {len(jockeys_page)} jockeys (total: {len(all_jockeys)})")

            # Check if there are more pages
            if len(jockeys_page) < limit_per_page:
                logger.info("Reached last page")
                break

            page += 1
            skip += limit_per_page

        logger.info(f"Total jockeys fetched from API: {len(all_jockeys)}")

        # Note: Regional filtering not available for jockeys in current API
        # All jockeys are stored - future enhancement could filter based on
        # UK/Ireland race participation
        if filter_uk_ireland:
            logger.info("Jockeys: UK/Ireland filtering not implemented (API limitation)")
            logger.info(f"Storing all {len(all_jockeys)} jockeys")

        # Transform data for database
        jockeys_transformed = []
        for jockey in all_jockeys:
            jockey_record = {
                'jockey_id': jockey.get('id'),
                'name': jockey.get('name'),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            jockeys_transformed.append(jockey_record)

        # Store in database
        if jockeys_transformed:
            db_stats = self.db_client.insert_jockeys(jockeys_transformed)
            logger.info(f"Database operation completed: {db_stats}")

            return {
                'success': True,
                'fetched': len(all_jockeys),
                'inserted': db_stats.get('inserted', 0),
                'api_stats': self.api_client.get_stats(),
                'db_stats': db_stats
            }
        else:
            logger.warning("No jockeys to insert")
            return {'success': False, 'error': 'No data to insert'}


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("JOCKEYS REFERENCE DATA FETCHER")
    logger.info("=" * 60)

    fetcher = JockeysFetcher()

    # Fetch all jockeys
    result = fetcher.fetch_and_store(limit_per_page=500)

    logger.info("\n" + "=" * 60)
    logger.info("FETCH COMPLETE")
    logger.info(f"Success: {result.get('success')}")
    logger.info(f"Fetched: {result.get('fetched', 0)} jockeys")
    logger.info(f"Inserted: {result.get('inserted', 0)} jockeys")
    logger.info("=" * 60)

    return result


if __name__ == '__main__':
    main()
