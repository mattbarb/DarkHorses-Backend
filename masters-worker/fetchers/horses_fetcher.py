"""
Horses Reference Data Fetcher
Fetches horse profiles from Racing API
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime
from typing import Dict, List
from config.config import get_config
from utils.logger import get_logger
from utils.api_client import RacingAPIClient
from utils.supabase_client import SupabaseReferenceClient
from utils.regional_filter import RegionalFilter

logger = get_logger('horses_fetcher')


class HorsesFetcher:
    """Fetcher for horse reference data"""

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
        Fetch horses from API and store in database

        Args:
            limit_per_page: Number of horses per page
            max_pages: Maximum pages to fetch (None = all)
            filter_uk_ireland: Filter to UK and Ireland horses only (default: True)

        Returns:
            Statistics dictionary
        """
        logger.info("Starting horses fetch")
        logger.info(f"UK/Ireland filtering: {'ENABLED' if filter_uk_ireland else 'DISABLED'}")

        all_horses = []
        page = 0
        skip = 0

        while True:
            if max_pages and page >= max_pages:
                logger.info(f"Reached max pages limit ({max_pages})")
                break

            # Fetch page
            logger.info(f"Fetching page {page + 1} (skip={skip})")
            api_response = self.api_client.search_horses(limit=limit_per_page, skip=skip)

            if not api_response or 'horses' not in api_response:
                logger.warning(f"No horses returned for page {page + 1}")
                break

            horses_page = api_response.get('horses', [])
            if not horses_page:
                logger.info("No more horses to fetch")
                break

            all_horses.extend(horses_page)
            logger.info(f"Fetched {len(horses_page)} horses (total: {len(all_horses)})")

            # Check if there are more pages
            if len(horses_page) < limit_per_page:
                logger.info("Reached last page")
                break

            page += 1
            skip += limit_per_page

        logger.info(f"Total horses fetched from API: {len(all_horses)}")

        # Filter to UK/Ireland only if requested
        if filter_uk_ireland:
            all_horses = RegionalFilter.filter_horses_by_region(all_horses)
            logger.info(f"After UK/Ireland filtering: {len(all_horses)} horses")

        # Transform data for database
        horses_transformed = []
        pedigrees_transformed = []

        for horse in all_horses:
            # Basic horse record
            horse_record = {
                'horse_id': horse.get('id'),
                'name': horse.get('name'),
                'dob': horse.get('dob'),
                'sex': horse.get('sex'),
                'sex_code': horse.get('sex_code'),
                'colour': horse.get('colour'),
                'region': horse.get('region'),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            horses_transformed.append(horse_record)

            # Pedigree data (if available)
            if any([horse.get('sire_id'), horse.get('dam_id'), horse.get('damsire_id')]):
                pedigree_record = {
                    'horse_id': horse.get('id'),
                    'sire_id': horse.get('sire_id'),
                    'sire': horse.get('sire'),
                    'sire_region': horse.get('sire_region'),
                    'dam_id': horse.get('dam_id'),
                    'dam': horse.get('dam'),
                    'dam_region': horse.get('dam_region'),
                    'damsire_id': horse.get('damsire_id'),
                    'damsire': horse.get('damsire'),
                    'damsire_region': horse.get('damsire_region'),
                    'breeder': horse.get('breeder'),
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                pedigrees_transformed.append(pedigree_record)

        # Store in database
        results = {}
        if horses_transformed:
            horse_stats = self.db_client.insert_horses(horses_transformed)
            results['horses'] = horse_stats
            logger.info(f"Horses inserted: {horse_stats}")

        if pedigrees_transformed:
            pedigree_stats = self.db_client.insert_pedigree(pedigrees_transformed)
            results['pedigrees'] = pedigree_stats
            logger.info(f"Pedigrees inserted: {pedigree_stats}")

        # Calculate statistics
        total_inserted = results.get('horses', {}).get('inserted', 0)

        return {
            'success': True,
            'fetched': len(all_horses),
            'inserted': total_inserted,  # For consistency with other fetchers
            'horses_inserted': total_inserted,
            'pedigrees_inserted': results.get('pedigrees', {}).get('inserted', 0),
            'api_stats': self.api_client.get_stats(),
            'db_stats': results
        }


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("HORSES REFERENCE DATA FETCHER")
    logger.info("=" * 60)

    fetcher = HorsesFetcher()

    # Fetch first 10 pages as a test (5000 horses)
    result = fetcher.fetch_and_store(limit_per_page=500, max_pages=10)

    logger.info("\n" + "=" * 60)
    logger.info("FETCH COMPLETE")
    logger.info(f"Success: {result.get('success')}")
    logger.info(f"Fetched: {result.get('fetched', 0)} horses")
    logger.info(f"Horses inserted: {result.get('horses_inserted', 0)}")
    logger.info(f"Pedigrees inserted: {result.get('pedigrees_inserted', 0)}")
    logger.info("=" * 60)

    return result


if __name__ == '__main__':
    main()
