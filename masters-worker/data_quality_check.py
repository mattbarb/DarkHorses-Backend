#!/usr/bin/env python3
"""
Data Quality Check Script for Racing API Reference Data

Validates data quality and completeness:
1. Table row counts
2. Data freshness (recent updates)
3. Data completeness (required fields)
4. Data consistency (relationships)
5. UK/Ireland filtering validation

Exit codes:
    0 - All quality checks passed
    1 - One or more quality checks failed
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from config.config import get_config
from utils.logger import get_logger
from utils.supabase_client import SupabaseClient

logger = get_logger('data_quality_check')


class DataQualityChecker:
    """Performs data quality checks"""

    # Quality thresholds
    EXPECTED_MINIMUMS = {
        'racing_courses': 50,  # UK + Ireland courses
        'racing_bookmakers': 5,  # Main UK bookmakers
        'racing_jockeys': 100,  # Active jockeys
        'racing_trainers': 100,  # Active trainers
        'racing_owners': 50,  # Common owners
        'racing_horses': 500,  # Active horses
        'racing_races': 10,  # Recent races
        'racing_results': 10  # Recent results
    }

    def __init__(self):
        """Initialize quality checker"""
        self.config = get_config()
        self.client = SupabaseClient()
        self.checks_passed = []
        self.checks_failed = []
        self.warnings = []

    def run_all_checks(self) -> bool:
        """
        Run all quality checks

        Returns:
            True if all critical checks pass, False otherwise
        """
        logger.info("=" * 80)
        logger.info("RACING API REFERENCE DATA - DATA QUALITY CHECK")
        logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
        logger.info("=" * 80)

        # Run checks
        self._check_table_counts()
        self._check_data_freshness()
        self._check_required_fields()
        self._check_regional_filtering()
        self._check_data_relationships()

        # Print summary
        self._print_summary()

        return len(self.checks_failed) == 0

    def _check_table_counts(self):
        """Check row counts in each table"""
        logger.info("\n[1/5] Checking Table Row Counts...")

        try:
            for table, expected_min in self.EXPECTED_MINIMUMS.items():
                try:
                    # Get count
                    result = self.client.client.table(table).select('id', count='exact').limit(1).execute()
                    count = result.count if hasattr(result, 'count') else 0

                    logger.info(f"  {table}: {count} rows")

                    if count < expected_min:
                        self.checks_failed.append({
                            'check': f'Row Count - {table}',
                            'status': 'FAILED',
                            'message': f'Only {count} rows (expected minimum {expected_min})'
                        })
                    elif count < expected_min * 2:
                        self.warnings.append({
                            'check': f'Row Count - {table}',
                            'status': 'WARNING',
                            'message': f'{count} rows (low but acceptable)'
                        })
                    else:
                        self.checks_passed.append({
                            'check': f'Row Count - {table}',
                            'status': 'PASSED',
                            'message': f'{count} rows'
                        })

                except Exception as e:
                    self.checks_failed.append({
                        'check': f'Row Count - {table}',
                        'status': 'ERROR',
                        'message': f'Failed to query table: {e}'
                    })

        except Exception as e:
            self.checks_failed.append({
                'check': 'Table Counts',
                'status': 'ERROR',
                'message': str(e)
            })
            logger.error(f"Table count check error: {e}")

    def _check_data_freshness(self):
        """Check data freshness (updated_at timestamps)"""
        logger.info("\n[2/5] Checking Data Freshness...")

        try:
            # Tables that should have recent updates
            daily_tables = ['racing_races', 'racing_results']
            weekly_tables = ['racing_horses', 'racing_jockeys', 'racing_trainers', 'racing_owners']

            # Check daily tables (updated within 48 hours)
            for table in daily_tables:
                try:
                    result = self.client.client.table(table)\
                        .select('updated_at')\
                        .order('updated_at', desc=True)\
                        .limit(1)\
                        .execute()

                    if result.data:
                        latest = datetime.fromisoformat(result.data[0]['updated_at'].replace('Z', '+00:00'))
                        age = datetime.utcnow() - latest.replace(tzinfo=None)

                        if age > timedelta(hours=48):
                            self.checks_failed.append({
                                'check': f'Freshness - {table}',
                                'status': 'FAILED',
                                'message': f'Last update {age.total_seconds() / 3600:.1f} hours ago'
                            })
                        else:
                            self.checks_passed.append({
                                'check': f'Freshness - {table}',
                                'status': 'PASSED',
                                'message': f'Updated {age.total_seconds() / 3600:.1f} hours ago'
                            })
                    else:
                        self.warnings.append({
                            'check': f'Freshness - {table}',
                            'status': 'WARNING',
                            'message': 'No data in table'
                        })

                except Exception as e:
                    logger.warning(f"Could not check freshness for {table}: {e}")

            # Check weekly tables (updated within 10 days)
            for table in weekly_tables:
                try:
                    result = self.client.client.table(table)\
                        .select('updated_at')\
                        .order('updated_at', desc=True)\
                        .limit(1)\
                        .execute()

                    if result.data:
                        latest = datetime.fromisoformat(result.data[0]['updated_at'].replace('Z', '+00:00'))
                        age = datetime.utcnow() - latest.replace(tzinfo=None)

                        if age > timedelta(days=10):
                            self.warnings.append({
                                'check': f'Freshness - {table}',
                                'status': 'WARNING',
                                'message': f'Last update {age.days} days ago'
                            })
                        else:
                            self.checks_passed.append({
                                'check': f'Freshness - {table}',
                                'status': 'PASSED',
                                'message': f'Updated {age.days} days ago'
                            })

                except Exception as e:
                    logger.warning(f"Could not check freshness for {table}: {e}")

        except Exception as e:
            self.checks_failed.append({
                'check': 'Data Freshness',
                'status': 'ERROR',
                'message': str(e)
            })
            logger.error(f"Freshness check error: {e}")

    def _check_required_fields(self):
        """Check for NULL values in required fields"""
        logger.info("\n[3/5] Checking Required Fields...")

        try:
            # Sample checks for critical fields
            checks = [
                ('racing_courses', 'name', 'Course name'),
                ('racing_courses', 'region_code', 'Region code'),
                ('racing_horses', 'name', 'Horse name'),
                ('racing_jockeys', 'name', 'Jockey name'),
                ('racing_trainers', 'name', 'Trainer name'),
                ('racing_races', 'course_id', 'Course ID'),
                ('racing_results', 'race_id', 'Race ID'),
            ]

            for table, field, description in checks:
                try:
                    # Count NULL values
                    result = self.client.client.table(table)\
                        .select(field, count='exact')\
                        .is_(field, 'null')\
                        .execute()

                    null_count = result.count if hasattr(result, 'count') else 0

                    if null_count > 0:
                        self.checks_failed.append({
                            'check': f'Required Field - {table}.{field}',
                            'status': 'FAILED',
                            'message': f'{null_count} NULL values found'
                        })
                    else:
                        self.checks_passed.append({
                            'check': f'Required Field - {table}.{field}',
                            'status': 'PASSED',
                            'message': 'No NULL values'
                        })

                except Exception as e:
                    logger.warning(f"Could not check {table}.{field}: {e}")

        except Exception as e:
            self.checks_failed.append({
                'check': 'Required Fields',
                'status': 'ERROR',
                'message': str(e)
            })
            logger.error(f"Required fields check error: {e}")

    def _check_regional_filtering(self):
        """Verify UK/Ireland filtering is working"""
        logger.info("\n[4/5] Checking Regional Filtering...")

        try:
            # Check courses are only GB/IRE
            result = self.client.client.table('racing_courses')\
                .select('region_code', count='exact')\
                .not_.in_('region_code', ['gb', 'ire'])\
                .execute()

            non_uk_ire = result.count if hasattr(result, 'count') else 0

            if non_uk_ire > 0:
                self.checks_failed.append({
                    'check': 'Regional Filtering - Courses',
                    'status': 'FAILED',
                    'message': f'{non_uk_ire} non-UK/Ireland courses found'
                })
            else:
                self.checks_passed.append({
                    'check': 'Regional Filtering - Courses',
                    'status': 'PASSED',
                    'message': 'All courses are UK/Ireland'
                })

            # Check races have UK/Ireland region codes
            result = self.client.client.table('racing_races')\
                .select('region_code', count='exact')\
                .not_.in_('region_code', ['gb', 'ire'])\
                .execute()

            non_uk_ire_races = result.count if hasattr(result, 'count') else 0

            if non_uk_ire_races > 0:
                self.checks_failed.append({
                    'check': 'Regional Filtering - Races',
                    'status': 'FAILED',
                    'message': f'{non_uk_ire_races} non-UK/Ireland races found'
                })
            else:
                self.checks_passed.append({
                    'check': 'Regional Filtering - Races',
                    'status': 'PASSED',
                    'message': 'All races are UK/Ireland'
                })

        except Exception as e:
            self.checks_failed.append({
                'check': 'Regional Filtering',
                'status': 'ERROR',
                'message': str(e)
            })
            logger.error(f"Regional filtering check error: {e}")

    def _check_data_relationships(self):
        """Check data relationships and referential integrity"""
        logger.info("\n[5/5] Checking Data Relationships...")

        try:
            # Check races have valid course references
            result = self.client.client.rpc('check_orphaned_races').execute()

            # Fallback: manual check
            races = self.client.client.table('racing_races').select('course_id').limit(100).execute()
            courses = self.client.client.table('racing_courses').select('id').execute()
            course_ids = {c['id'] for c in courses.data} if courses.data else set()

            orphaned = sum(1 for r in (races.data or []) if r['course_id'] not in course_ids)

            if orphaned > 0:
                self.warnings.append({
                    'check': 'Data Relationships - Races',
                    'status': 'WARNING',
                    'message': f'{orphaned} races with invalid course references (sample of 100)'
                })
            else:
                self.checks_passed.append({
                    'check': 'Data Relationships - Races',
                    'status': 'PASSED',
                    'message': 'All race course references valid (sample)'
                })

        except Exception as e:
            logger.warning(f"Relationship check error: {e}")
            self.warnings.append({
                'check': 'Data Relationships',
                'status': 'WARNING',
                'message': f'Could not verify relationships: {e}'
            })

    def _print_summary(self):
        """Print quality check summary"""
        logger.info("\n" + "=" * 80)
        logger.info("DATA QUALITY CHECK SUMMARY")
        logger.info("=" * 80)

        # Print passed checks
        if self.checks_passed:
            logger.info(f"\nPassed Checks ({len(self.checks_passed)}):")
            for check in self.checks_passed[:10]:  # Show first 10
                logger.info(f"  [PASS] {check['check']}: {check['message']}")
            if len(self.checks_passed) > 10:
                logger.info(f"  ... and {len(self.checks_passed) - 10} more")

        # Print warnings
        if self.warnings:
            logger.info(f"\nWarnings ({len(self.warnings)}):")
            for check in self.warnings:
                logger.warning(f"  [WARN] {check['check']}: {check['message']}")

        # Print failed checks
        if self.checks_failed:
            logger.info(f"\nFailed Checks ({len(self.checks_failed)}):")
            for check in self.checks_failed:
                logger.error(f"  [FAIL] {check['check']}: {check['message']}")

        # Overall status
        total = len(self.checks_passed) + len(self.checks_failed) + len(self.warnings)
        logger.info(f"\nOverall: {len(self.checks_passed)}/{total} checks passed")
        logger.info(f"Warnings: {len(self.warnings)}")
        logger.info(f"Failures: {len(self.checks_failed)}")

        if len(self.checks_failed) == 0:
            logger.info("Data quality is GOOD")
        else:
            logger.warning("Data quality has ISSUES - review failed checks")

        logger.info("=" * 80)


def main():
    """Main execution"""
    try:
        checker = DataQualityChecker()
        all_passed = checker.run_all_checks()

        sys.exit(0 if all_passed else 1)

    except Exception as e:
        logger.error(f"Data quality check failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
