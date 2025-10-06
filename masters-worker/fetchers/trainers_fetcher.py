"""
Trainers Reference Data Fetcher
Fetches trainer profiles from Racing API
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

logger = get_logger('trainers_fetcher')


class TrainersFetcher:
    """Fetcher for trainer reference data"""

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
        Fetch trainers from API and store in database

        Args:
            limit_per_page: Number of trainers per page
            max_pages: Maximum pages to fetch (None = all)
            filter_uk_ireland: Filter to UK and Ireland trainers only (default: True)

        Returns:
            Statistics dictionary
        """
        logger.info("Starting trainers fetch")
        logger.info(f"UK/Ireland filtering: {'ENABLED' if filter_uk_ireland else 'DISABLED'}")

        all_trainers = []
        page = 0
        skip = 0

        while True:
            if max_pages and page >= max_pages:
                logger.info(f"Reached max pages limit ({max_pages})")
                break

            # Fetch page
            logger.info(f"Fetching page {page + 1} (skip={skip})")
            api_response = self.api_client.search_trainers(limit=limit_per_page, skip=skip)

            if not api_response or 'trainers' not in api_response:
                logger.warning(f"No trainers returned for page {page + 1}")
                break

            trainers_page = api_response.get('trainers', [])
            if not trainers_page:
                logger.info("No more trainers to fetch")
                break

            all_trainers.extend(trainers_page)
            logger.info(f"Fetched {len(trainers_page)} trainers (total: {len(all_trainers)})")

            # Check if there are more pages
            if len(trainers_page) < limit_per_page:
                logger.info("Reached last page")
                break

            page += 1
            skip += limit_per_page

        logger.info(f"Total trainers fetched from API: {len(all_trainers)}")

        # Filter to UK/Ireland only if requested
        if filter_uk_ireland:
            all_trainers = RegionalFilter.filter_trainers_by_location(all_trainers)
            logger.info(f"After UK/Ireland filtering: {len(all_trainers)} trainers")

        # Transform data for database
        trainers_transformed = []
        for trainer in all_trainers:
            trainer_record = {
                'trainer_id': trainer.get('id'),
                'name': trainer.get('name'),
                'location': trainer.get('location'),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            trainers_transformed.append(trainer_record)

        # Store in database
        if trainers_transformed:
            db_stats = self.db_client.insert_trainers(trainers_transformed)
            logger.info(f"Database operation completed: {db_stats}")

            return {
                'success': True,
                'fetched': len(all_trainers),
                'inserted': db_stats.get('inserted', 0),
                'api_stats': self.api_client.get_stats(),
                'db_stats': db_stats
            }
        else:
            logger.warning("No trainers to insert")
            return {'success': False, 'error': 'No data to insert'}


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("TRAINERS REFERENCE DATA FETCHER")
    logger.info("=" * 60)

    fetcher = TrainersFetcher()

    # Fetch all trainers
    result = fetcher.fetch_and_store(limit_per_page=500)

    logger.info("\n" + "=" * 60)
    logger.info("FETCH COMPLETE")
    logger.info(f"Success: {result.get('success')}")
    logger.info(f"Fetched: {result.get('fetched', 0)} trainers")
    logger.info(f"Inserted: {result.get('inserted', 0)} trainers")
    logger.info("=" * 60)

    return result


if __name__ == '__main__':
    main()
