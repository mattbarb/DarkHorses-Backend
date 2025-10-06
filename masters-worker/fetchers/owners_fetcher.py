"""
Owners Reference Data Fetcher
Fetches owner profiles from Racing API
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

logger = get_logger('owners_fetcher')


class OwnersFetcher:
    """Fetcher for owner reference data"""

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
        Fetch owners from API and store in database

        Args:
            limit_per_page: Number of owners per page
            max_pages: Maximum pages to fetch (None = all)
            filter_uk_ireland: Filter to UK and Ireland owners only (default: True)
                             Note: API doesn't provide region data for owners,
                             so this currently includes all owners.
                             Future enhancement: filter based on horse ownership.

        Returns:
            Statistics dictionary
        """
        logger.info("Starting owners fetch")
        if filter_uk_ireland:
            logger.warning("UK/Ireland filtering requested but not available for owners API endpoint")
            logger.warning("Fetching all owners - consider implementing ownership-based filtering")

        all_owners = []
        page = 0
        skip = 0

        while True:
            if max_pages and page >= max_pages:
                logger.info(f"Reached max pages limit ({max_pages})")
                break

            # Fetch page
            logger.info(f"Fetching page {page + 1} (skip={skip})")
            api_response = self.api_client.search_owners(limit=limit_per_page, skip=skip)

            if not api_response or 'owners' not in api_response:
                logger.warning(f"No owners returned for page {page + 1}")
                break

            owners_page = api_response.get('owners', [])
            if not owners_page:
                logger.info("No more owners to fetch")
                break

            all_owners.extend(owners_page)
            logger.info(f"Fetched {len(owners_page)} owners (total: {len(all_owners)})")

            # Check if there are more pages
            if len(owners_page) < limit_per_page:
                logger.info("Reached last page")
                break

            page += 1
            skip += limit_per_page

        logger.info(f"Total owners fetched from API: {len(all_owners)}")

        # Note: Regional filtering not available for owners in current API
        # All owners are stored - future enhancement could filter based on
        # UK/Ireland horse ownership
        if filter_uk_ireland:
            logger.info("Owners: UK/Ireland filtering not implemented (API limitation)")
            logger.info(f"Storing all {len(all_owners)} owners")

        # Transform data for database
        owners_transformed = []
        for owner in all_owners:
            owner_record = {
                'owner_id': owner.get('id'),
                'name': owner.get('name'),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            owners_transformed.append(owner_record)

        # Store in database
        if owners_transformed:
            db_stats = self.db_client.insert_owners(owners_transformed)
            logger.info(f"Database operation completed: {db_stats}")

            return {
                'success': True,
                'fetched': len(all_owners),
                'inserted': db_stats.get('inserted', 0),
                'api_stats': self.api_client.get_stats(),
                'db_stats': db_stats
            }
        else:
            logger.warning("No owners to insert")
            return {'success': False, 'error': 'No data to insert'}


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("OWNERS REFERENCE DATA FETCHER")
    logger.info("=" * 60)

    fetcher = OwnersFetcher()

    # Fetch all owners
    result = fetcher.fetch_and_store(limit_per_page=500)

    logger.info("\n" + "=" * 60)
    logger.info("FETCH COMPLETE")
    logger.info(f"Success: {result.get('success')}")
    logger.info(f"Fetched: {result.get('fetched', 0)} owners")
    logger.info(f"Inserted: {result.get('inserted', 0)} owners")
    logger.info("=" * 60)

    return result


if __name__ == '__main__':
    main()
