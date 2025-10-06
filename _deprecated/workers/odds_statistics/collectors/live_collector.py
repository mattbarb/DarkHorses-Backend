"""
Statistics collector for ra_odds_live table
"""
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class LiveOddsCollector:
    """Collects statistics for ra_odds_live table"""

    def __init__(self, db_connection):
        self.db = db_connection
        self.table_name = 'ra_odds_live'

    def collect_all_stats(self) -> Dict:
        """Collect all ra_odds_live statistics"""
        logger.info(f"Collecting statistics for {self.table_name}...")

        return {
            'basic_metrics': self.collect_basic_metrics(),
            'recent_activity': self.collect_recent_activity(),
            'unique_entities': self.collect_unique_entities(),
            'bookmaker_coverage': self.collect_bookmaker_coverage(),
            'records_per_date': self.collect_records_per_date(),
            'course_distribution': self.collect_course_distribution(),
            'data_quality': self.collect_data_quality(),
            'market_status': self.collect_market_status()
        }

    def collect_basic_metrics(self) -> Dict:
        """Collect basic volume metrics"""
        total = self.db.execute_scalar(f"SELECT COUNT(*) FROM {self.table_name}")

        earliest_race_date = self.db.execute_scalar(
            f"SELECT MIN(race_date) FROM {self.table_name}"
        )
        latest_race_date = self.db.execute_scalar(
            f"SELECT MAX(race_date) FROM {self.table_name}"
        )
        latest_odds_timestamp = self.db.execute_scalar(
            f"SELECT MAX(odds_timestamp) FROM {self.table_name}"
        )
        latest_fetch = self.db.execute_scalar(
            f"SELECT MAX(fetched_at) FROM {self.table_name}"
        )

        return {
            'total_records': total or 0,
            'earliest_race_date': str(earliest_race_date) if earliest_race_date else None,
            'latest_race_date': str(latest_race_date) if latest_race_date else None,
            'latest_odds_timestamp': str(latest_odds_timestamp) if latest_odds_timestamp else None,
            'latest_fetch': str(latest_fetch) if latest_fetch else None
        }

    def collect_recent_activity(self) -> Dict:
        """Collect recent activity metrics"""
        last_hour = self.db.execute_scalar(
            f"SELECT COUNT(*) FROM {self.table_name} WHERE fetched_at >= NOW() - INTERVAL '1 hour'"
        )
        last_24h = self.db.execute_scalar(
            f"SELECT COUNT(*) FROM {self.table_name} WHERE fetched_at >= NOW() - INTERVAL '1 day'"
        )

        return {
            'records_last_hour': last_hour or 0,
            'records_last_24h': last_24h or 0
        }

    def collect_unique_entities(self) -> Dict:
        """Collect unique entity counts"""
        races = self.db.execute_scalar(
            f"SELECT COUNT(DISTINCT race_id) FROM {self.table_name}"
        )
        horses = self.db.execute_scalar(
            f"SELECT COUNT(DISTINCT horse_id) FROM {self.table_name}"
        )
        courses = self.db.execute_scalar(
            f"SELECT COUNT(DISTINCT course) FROM {self.table_name} WHERE course IS NOT NULL"
        )
        bookmakers = self.db.execute_scalar(
            f"SELECT COUNT(DISTINCT bookmaker_id) FROM {self.table_name}"
        )

        return {
            'unique_races': races or 0,
            'unique_horses': horses or 0,
            'unique_courses': courses or 0,
            'unique_bookmakers': bookmakers or 0
        }

    def collect_bookmaker_coverage(self) -> List[Dict]:
        """Collect bookmaker coverage statistics"""
        query = f"""
            SELECT
                bookmaker_id,
                bookmaker_name,
                bookmaker_type,
                COUNT(*) as odds_count,
                COUNT(DISTINCT race_id) as races_covered,
                COUNT(DISTINCT horse_id) as horses_covered,
                MAX(odds_timestamp) as latest_odds
            FROM {self.table_name}
            GROUP BY bookmaker_id, bookmaker_name, bookmaker_type
            ORDER BY odds_count DESC
        """
        return self.db.execute_query(query)

    def collect_records_per_date(self, days: int = 7) -> List[Dict]:
        """Collect records per date for last N days"""
        query = f"""
            SELECT
                race_date,
                COUNT(*) as record_count,
                COUNT(DISTINCT race_id) as unique_races,
                COUNT(DISTINCT bookmaker_id) as unique_bookmakers
            FROM {self.table_name}
            WHERE race_date >= CURRENT_DATE - INTERVAL '{days} days'
            GROUP BY race_date
            ORDER BY race_date DESC
        """
        return self.db.execute_query(query)

    def collect_course_distribution(self, limit: int = 20) -> List[Dict]:
        """Collect course distribution"""
        query = f"""
            SELECT
                course,
                COUNT(*) as record_count,
                COUNT(DISTINCT race_id) as unique_races,
                COUNT(DISTINCT bookmaker_id) as unique_bookmakers
            FROM {self.table_name}
            WHERE course IS NOT NULL
            GROUP BY course
            ORDER BY record_count DESC
            LIMIT {limit}
        """
        return self.db.execute_query(query)

    def collect_data_quality(self) -> Dict:
        """Collect data quality metrics"""
        query = f"""
            SELECT
                COUNT(*) FILTER (WHERE race_id IS NULL) as null_race_id,
                COUNT(*) FILTER (WHERE horse_id IS NULL) as null_horse_id,
                COUNT(*) FILTER (WHERE bookmaker_id IS NULL) as null_bookmaker_id,
                COUNT(*) FILTER (WHERE race_date IS NULL) as null_race_date,
                COUNT(*) FILTER (WHERE course IS NULL) as null_course,
                COUNT(*) FILTER (WHERE horse_name IS NULL) as null_horse_name,
                COUNT(*) FILTER (WHERE odds_decimal IS NULL) as null_odds_decimal,
                COUNT(*) FILTER (WHERE odds_timestamp IS NULL) as null_odds_timestamp,
                COUNT(*) as total_records
            FROM {self.table_name}
        """
        results = self.db.execute_query(query)
        return results[0] if results else {}

    def collect_market_status(self) -> List[Dict]:
        """Collect market status distribution"""
        query = f"""
            SELECT
                market_status,
                COUNT(*) as record_count,
                ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM {self.table_name}), 2) as percentage
            FROM {self.table_name}
            GROUP BY market_status
            ORDER BY record_count DESC
        """
        return self.db.execute_query(query)
