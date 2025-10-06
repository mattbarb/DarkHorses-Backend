"""
Courses Reference Data Fetcher
Fetches course/track information from Racing API
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

logger = get_logger('courses_fetcher')


class CoursesFetcher:
    """Fetcher for course reference data"""

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

    def fetch_and_store(self, region_codes: List[str] = None) -> Dict:
        """
        Fetch courses from API and store in database

        Args:
            region_codes: Optional list of region codes to filter (e.g., ['gb', 'ire'])

        Returns:
            Statistics dictionary
        """
        logger.info("Starting courses fetch")

        # Fetch from API
        api_response = self.api_client.get_courses(region_codes=region_codes)

        if not api_response or 'courses' not in api_response:
            logger.error("Failed to fetch courses from API")
            return {'success': False, 'error': 'API fetch failed'}

        courses_raw = api_response.get('courses', [])
        logger.info(f"Fetched {len(courses_raw)} courses from API")

        # Transform data for database
        courses_transformed = []
        for course in courses_raw:
            course_record = {
                'course_id': course.get('id'),
                'name': course.get('course'),  # API returns 'course' not 'name'
                'region': course.get('region_code'),  # Use region_code
                'country': course.get('region'),  # Full region name
                'latitude': None,  # Not provided by courses endpoint
                'longitude': None,  # Not provided by courses endpoint
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            courses_transformed.append(course_record)

        # Store in database
        if courses_transformed:
            db_stats = self.db_client.insert_courses(courses_transformed)
            logger.info(f"Database operation completed: {db_stats}")

            return {
                'success': True,
                'fetched': len(courses_raw),
                'inserted': db_stats.get('inserted', 0),
                'api_stats': self.api_client.get_stats(),
                'db_stats': db_stats
            }
        else:
            logger.warning("No courses to insert")
            return {'success': False, 'error': 'No data to insert'}


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("COURSES REFERENCE DATA FETCHER")
    logger.info("=" * 60)

    fetcher = CoursesFetcher()

    # Fetch UK and Irish courses
    result = fetcher.fetch_and_store(region_codes=['gb', 'ire'])

    logger.info("\n" + "=" * 60)
    logger.info("FETCH COMPLETE")
    logger.info(f"Success: {result.get('success')}")
    logger.info(f"Fetched: {result.get('fetched', 0)} courses")
    logger.info(f"Inserted: {result.get('inserted', 0)} courses")
    logger.info("=" * 60)

    return result


if __name__ == '__main__':
    main()
