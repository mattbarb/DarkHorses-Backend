"""
Statistics collector for ra_odds_historical table
"""
import logging
from typing import Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HistoricalOddsCollector:
    """Collects statistics for ra_odds_historical table"""

    def __init__(self, db_connection):
        self.db = db_connection
        self.table_name = 'ra_odds_historical'

    def collect_all_stats(self) -> Dict:
        """Collect all ra_odds_historical statistics"""
        logger.info(f"Collecting statistics for {self.table_name}...")

        return {
            'basic_metrics': self.collect_basic_metrics(),
            'recent_activity': self.collect_recent_activity(),
            'unique_entities': self.collect_unique_entities(),
            'records_per_date': self.collect_records_per_date(),
            'country_distribution': self.collect_country_distribution(),
            'track_distribution': self.collect_track_distribution(),
            'data_quality': self.collect_data_quality(),
            'odds_coverage': self.collect_odds_coverage()
        }

    def collect_basic_metrics(self) -> Dict:
        """Collect basic volume metrics"""
        total = self.db.execute_scalar(f"SELECT COUNT(*) FROM {self.table_name}")

        earliest_date = self.db.execute_scalar(
            f"SELECT MIN(date_of_race) FROM {self.table_name}"
        )
        latest_date = self.db.execute_scalar(
            f"SELECT MAX(date_of_race) FROM {self.table_name}"
        )
        latest_update = self.db.execute_scalar(
            f"SELECT MAX(updated_at) FROM {self.table_name}"
        )

        # Calculate date range
        date_range_days = None
        if earliest_date and latest_date:
            if isinstance(earliest_date, str):
                earliest_date = datetime.fromisoformat(earliest_date)
            if isinstance(latest_date, str):
                latest_date = datetime.fromisoformat(latest_date)
            date_range_days = (latest_date - earliest_date).days

        return {
            'total_records': total or 0,
            'earliest_race_date': str(earliest_date) if earliest_date else None,
            'latest_race_date': str(latest_date) if latest_date else None,
            'date_range_days': date_range_days,
            'latest_update': str(latest_update) if latest_update else None
        }

    def collect_recent_activity(self) -> Dict:
        """Collect recent activity metrics"""
        last_hour = self.db.execute_scalar(
            f"SELECT COUNT(*) FROM {self.table_name} WHERE created_at >= NOW() - INTERVAL '1 hour'"
        )
        last_24h = self.db.execute_scalar(
            f"SELECT COUNT(*) FROM {self.table_name} WHERE created_at >= NOW() - INTERVAL '1 day'"
        )
        last_7d = self.db.execute_scalar(
            f"SELECT COUNT(*) FROM {self.table_name} WHERE created_at >= NOW() - INTERVAL '7 days'"
        )

        return {
            'records_last_hour': last_hour or 0,
            'records_last_24h': last_24h or 0,
            'records_last_7d': last_7d or 0
        }

    def collect_unique_entities(self) -> Dict:
        """Collect unique entity counts"""
        horses = self.db.execute_scalar(
            f"SELECT COUNT(DISTINCT horse_name) FROM {self.table_name} WHERE horse_name IS NOT NULL"
        )
        tracks = self.db.execute_scalar(
            f"SELECT COUNT(DISTINCT track) FROM {self.table_name} WHERE track IS NOT NULL"
        )
        jockeys = self.db.execute_scalar(
            f"SELECT COUNT(DISTINCT jockey) FROM {self.table_name} WHERE jockey IS NOT NULL"
        )
        trainers = self.db.execute_scalar(
            f"SELECT COUNT(DISTINCT trainer) FROM {self.table_name} WHERE trainer IS NOT NULL"
        )
        countries = self.db.execute_scalar(
            f"SELECT COUNT(DISTINCT country) FROM {self.table_name} WHERE country IS NOT NULL"
        )

        return {
            'unique_horses': horses or 0,
            'unique_tracks': tracks or 0,
            'unique_jockeys': jockeys or 0,
            'unique_trainers': trainers or 0,
            'unique_countries': countries or 0
        }

    def collect_records_per_date(self, days: int = 7) -> List[Dict]:
        """Collect records per date for last N days"""
        query = f"""
            SELECT
                DATE(date_of_race) as race_date,
                COUNT(*) as record_count
            FROM {self.table_name}
            WHERE date_of_race >= CURRENT_DATE - INTERVAL '{days} days'
            GROUP BY DATE(date_of_race)
            ORDER BY race_date DESC
        """
        return self.db.execute_query(query)

    def collect_country_distribution(self, limit: int = 10) -> List[Dict]:
        """Collect country distribution"""
        query = f"""
            SELECT
                country,
                COUNT(*) as record_count,
                ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM {self.table_name}), 2) as percentage
            FROM {self.table_name}
            WHERE country IS NOT NULL
            GROUP BY country
            ORDER BY record_count DESC
            LIMIT {limit}
        """
        return self.db.execute_query(query)

    def collect_track_distribution(self, limit: int = 20) -> List[Dict]:
        """Collect track distribution"""
        query = f"""
            SELECT
                track,
                COUNT(*) as record_count
            FROM {self.table_name}
            WHERE track IS NOT NULL
            GROUP BY track
            ORDER BY record_count DESC
            LIMIT {limit}
        """
        return self.db.execute_query(query)

    def collect_data_quality(self) -> Dict:
        """Collect data quality metrics"""
        query = f"""
            SELECT
                COUNT(*) FILTER (WHERE date_of_race IS NULL) as null_date_of_race,
                COUNT(*) FILTER (WHERE track IS NULL) as null_track,
                COUNT(*) FILTER (WHERE horse_name IS NULL) as null_horse_name,
                COUNT(*) FILTER (WHERE industry_sp IS NULL) as null_industry_sp,
                COUNT(*) FILTER (WHERE finishing_position IS NULL) as null_finishing_position,
                COUNT(*) FILTER (WHERE jockey IS NULL) as null_jockey,
                COUNT(*) FILTER (WHERE trainer IS NULL) as null_trainer,
                COUNT(*) FILTER (WHERE country IS NULL) as null_country,
                COUNT(*) as total_records
            FROM {self.table_name}
        """
        results = self.db.execute_query(query)
        return results[0] if results else {}

    def collect_odds_coverage(self) -> Dict:
        """Collect odds data coverage metrics"""
        query = f"""
            SELECT
                COUNT(*) FILTER (WHERE industry_sp IS NOT NULL) as has_industry_sp,
                COUNT(*) FILTER (WHERE pre_race_min IS NOT NULL) as has_pre_race_min,
                COUNT(*) FILTER (WHERE pre_race_max IS NOT NULL) as has_pre_race_max,
                COUNT(*) FILTER (WHERE forecasted_odds IS NOT NULL) as has_forecasted_odds,
                COUNT(*) as total_records
            FROM {self.table_name}
        """
        results = self.db.execute_query(query)
        return results[0] if results else {}
