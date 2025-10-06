"""
Bookmakers Reference Data Fetcher
Populates static bookmaker reference data
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime
from typing import Dict, List
from config.config import get_config
from utils.logger import get_logger
from utils.supabase_client import SupabaseReferenceClient

logger = get_logger('bookmakers_fetcher')


class BookmakersFetcher:
    """Fetcher for bookmaker reference data"""

    # Static list of major UK/Irish bookmakers
    BOOKMAKERS = [
        {'id': 'bet365', 'name': 'Bet365', 'type': 'online'},
        {'id': 'william_hill', 'name': 'William Hill', 'type': 'online'},
        {'id': 'ladbrokes', 'name': 'Ladbrokes', 'type': 'online'},
        {'id': 'coral', 'name': 'Coral', 'type': 'online'},
        {'id': 'paddy_power', 'name': 'Paddy Power', 'type': 'online'},
        {'id': 'betfair', 'name': 'Betfair', 'type': 'exchange'},
        {'id': 'betfair_sportsbook', 'name': 'Betfair Sportsbook', 'type': 'online'},
        {'id': 'skybet', 'name': 'Sky Bet', 'type': 'online'},
        {'id': 'betvictor', 'name': 'BetVictor', 'type': 'online'},
        {'id': 'betfred', 'name': 'Betfred', 'type': 'online'},
        {'id': '888sport', 'name': '888sport', 'type': 'online'},
        {'id': 'unibet', 'name': 'Unibet', 'type': 'online'},
        {'id': 'betway', 'name': 'Betway', 'type': 'online'},
        {'id': 'boylesports', 'name': 'BoyleSports', 'type': 'online'},
        {'id': 'betdaq', 'name': 'Betdaq', 'type': 'exchange'},
        {'id': 'matchbook', 'name': 'Matchbook', 'type': 'exchange'},
        {'id': 'smarkets', 'name': 'Smarkets', 'type': 'exchange'},
        {'id': 'spreadex', 'name': 'Spreadex', 'type': 'spread'},
        {'id': 'sporting_index', 'name': 'Sporting Index', 'type': 'spread'},
    ]

    def __init__(self):
        """Initialize fetcher"""
        self.config = get_config()
        self.db_client = SupabaseReferenceClient(
            url=self.config.supabase.url,
            service_key=self.config.supabase.service_key,
            batch_size=self.config.supabase.batch_size
        )

    def fetch_and_store(self) -> Dict:
        """
        Store bookmakers in database

        Returns:
            Statistics dictionary
        """
        logger.info("Starting bookmakers insert")

        # Transform data for database
        bookmakers_transformed = []
        for bookmaker in self.BOOKMAKERS:
            bookmaker_record = {
                'bookmaker_id': bookmaker['id'],
                'bookmaker_name': bookmaker['name'],
                'bookmaker_type': bookmaker['type'],
                'active': True,
                'created_at': datetime.utcnow().isoformat()
            }
            bookmakers_transformed.append(bookmaker_record)

        logger.info(f"Inserting {len(bookmakers_transformed)} bookmakers")

        # Store in database
        if bookmakers_transformed:
            db_stats = self.db_client.insert_bookmakers(bookmakers_transformed)
            logger.info(f"Database operation completed: {db_stats}")

            return {
                'success': True,
                'inserted': db_stats.get('inserted', 0),
                'db_stats': db_stats
            }
        else:
            logger.warning("No bookmakers to insert")
            return {'success': False, 'error': 'No data to insert'}


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("BOOKMAKERS REFERENCE DATA FETCHER")
    logger.info("=" * 60)

    fetcher = BookmakersFetcher()

    # Insert bookmakers
    result = fetcher.fetch_and_store()

    logger.info("\n" + "=" * 60)
    logger.info("FETCH COMPLETE")
    logger.info(f"Success: {result.get('success')}")
    logger.info(f"Inserted: {result.get('inserted', 0)} bookmakers")
    logger.info("=" * 60)

    return result


if __name__ == '__main__':
    main()
