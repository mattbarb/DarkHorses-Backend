#!/usr/bin/env python3
"""
Health Check Script for Racing API Reference Data Fetcher

Verifies that:
1. Environment is properly configured
2. Racing API is accessible
3. Supabase database is accessible
4. Recent fetches are running successfully
5. No critical errors in logs

Exit codes:
    0 - All health checks passed
    1 - One or more health checks failed
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from config.config import get_config
from utils.logger import get_logger
from utils.api_client import RacingAPIClient
from utils.supabase_client import SupabaseClient

logger = get_logger('health_check')


class HealthChecker:
    """Performs system health checks"""

    def __init__(self):
        """Initialize health checker"""
        self.config = get_config()
        self.checks_passed = []
        self.checks_failed = []

    def run_all_checks(self) -> bool:
        """
        Run all health checks

        Returns:
            True if all checks pass, False otherwise
        """
        logger.info("=" * 80)
        logger.info("RACING API REFERENCE DATA FETCHER - HEALTH CHECK")
        logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
        logger.info("=" * 80)

        # Run checks
        self._check_environment()
        self._check_racing_api()
        self._check_supabase()
        self._check_recent_fetches()
        self._check_error_logs()

        # Print summary
        self._print_summary()

        return len(self.checks_failed) == 0

    def _check_environment(self):
        """Check environment configuration"""
        logger.info("\n[1/5] Checking Environment Configuration...")

        try:
            # Check required environment variables
            issues = []

            if not self.config.api.username:
                issues.append("Missing RACING_API_USERNAME")

            if not self.config.api.password:
                issues.append("Missing RACING_API_PASSWORD")

            if not self.config.supabase.url:
                issues.append("Missing SUPABASE_URL")

            if not self.config.supabase.service_key:
                issues.append("Missing SUPABASE_SERVICE_KEY")

            if issues:
                self.checks_failed.append({
                    'check': 'Environment',
                    'status': 'FAILED',
                    'message': '; '.join(issues)
                })
                logger.error(f"Environment check failed: {', '.join(issues)}")
            else:
                self.checks_passed.append({
                    'check': 'Environment',
                    'status': 'PASSED',
                    'message': 'All environment variables configured'
                })
                logger.info("Environment configuration: OK")

        except Exception as e:
            self.checks_failed.append({
                'check': 'Environment',
                'status': 'ERROR',
                'message': str(e)
            })
            logger.error(f"Environment check error: {e}")

    def _check_racing_api(self):
        """Check Racing API connectivity"""
        logger.info("\n[2/5] Checking Racing API Connection...")

        try:
            client = RacingAPIClient()

            # Try to fetch courses (small dataset)
            response = client.get('/courses', params={'limit_per_page': 1, 'region_code': 'gb'})

            if response and isinstance(response, dict):
                self.checks_passed.append({
                    'check': 'Racing API',
                    'status': 'PASSED',
                    'message': 'API accessible and responding'
                })
                logger.info("Racing API connection: OK")
            else:
                self.checks_failed.append({
                    'check': 'Racing API',
                    'status': 'FAILED',
                    'message': 'API returned unexpected response'
                })
                logger.error("Racing API check failed: unexpected response")

        except Exception as e:
            self.checks_failed.append({
                'check': 'Racing API',
                'status': 'ERROR',
                'message': str(e)
            })
            logger.error(f"Racing API check error: {e}")

    def _check_supabase(self):
        """Check Supabase database connectivity"""
        logger.info("\n[3/5] Checking Supabase Database Connection...")

        try:
            client = SupabaseClient()

            # Try to query courses table (should exist)
            result = client.client.table('racing_courses').select('id').limit(1).execute()

            if result.data is not None:
                self.checks_passed.append({
                    'check': 'Supabase',
                    'status': 'PASSED',
                    'message': 'Database accessible and responding'
                })
                logger.info("Supabase connection: OK")
            else:
                self.checks_failed.append({
                    'check': 'Supabase',
                    'status': 'FAILED',
                    'message': 'Database query returned no data'
                })
                logger.error("Supabase check failed: no data")

        except Exception as e:
            self.checks_failed.append({
                'check': 'Supabase',
                'status': 'ERROR',
                'message': str(e)
            })
            logger.error(f"Supabase check error: {e}")

    def _check_recent_fetches(self):
        """Check recent fetch results"""
        logger.info("\n[4/5] Checking Recent Fetch Results...")

        try:
            # Find most recent results file
            logs_dir = self.config.paths.logs_dir
            result_files = sorted(logs_dir.glob('fetch_results_*.json'), reverse=True)

            if not result_files:
                self.checks_failed.append({
                    'check': 'Recent Fetches',
                    'status': 'WARNING',
                    'message': 'No fetch results found - system may not have run yet'
                })
                logger.warning("No fetch results found")
                return

            # Check most recent file
            latest_file = result_files[0]
            with open(latest_file) as f:
                results = json.load(f)

            # Check if recent (within 48 hours)
            end_time = datetime.fromisoformat(results['end_time'].replace('Z', '+00:00'))
            age = datetime.utcnow() - end_time.replace(tzinfo=None)

            if age > timedelta(hours=48):
                self.checks_failed.append({
                    'check': 'Recent Fetches',
                    'status': 'WARNING',
                    'message': f'Last fetch was {age.total_seconds() / 3600:.1f} hours ago'
                })
                logger.warning(f"Last fetch is old: {age.total_seconds() / 3600:.1f} hours")
            else:
                # Check for failures
                failures = [k for k, v in results['results'].items() if not v.get('success')]

                if failures:
                    self.checks_failed.append({
                        'check': 'Recent Fetches',
                        'status': 'WARNING',
                        'message': f'Last fetch had failures: {", ".join(failures)}'
                    })
                    logger.warning(f"Last fetch had failures: {failures}")
                else:
                    self.checks_passed.append({
                        'check': 'Recent Fetches',
                        'status': 'PASSED',
                        'message': f'Last fetch successful ({age.total_seconds() / 3600:.1f} hours ago)'
                    })
                    logger.info(f"Recent fetches: OK ({age.total_seconds() / 3600:.1f} hours ago)")

        except Exception as e:
            self.checks_failed.append({
                'check': 'Recent Fetches',
                'status': 'ERROR',
                'message': str(e)
            })
            logger.error(f"Recent fetch check error: {e}")

    def _check_error_logs(self):
        """Check for recent errors in log files"""
        logger.info("\n[5/5] Checking Error Logs...")

        try:
            # Check main log file
            log_file = self.config.paths.logs_dir / 'main.log'

            if not log_file.exists():
                self.checks_passed.append({
                    'check': 'Error Logs',
                    'status': 'PASSED',
                    'message': 'No log file yet (new installation)'
                })
                logger.info("No log file found (new installation)")
                return

            # Read last 100 lines and count errors
            with open(log_file) as f:
                lines = f.readlines()[-100:]

            error_count = sum(1 for line in lines if 'ERROR' in line or 'CRITICAL' in line)

            if error_count > 10:
                self.checks_failed.append({
                    'check': 'Error Logs',
                    'status': 'WARNING',
                    'message': f'{error_count} errors found in recent logs'
                })
                logger.warning(f"{error_count} errors in recent logs")
            else:
                self.checks_passed.append({
                    'check': 'Error Logs',
                    'status': 'PASSED',
                    'message': f'{error_count} errors in recent logs (acceptable)'
                })
                logger.info(f"Error logs: OK ({error_count} errors)")

        except Exception as e:
            self.checks_failed.append({
                'check': 'Error Logs',
                'status': 'ERROR',
                'message': str(e)
            })
            logger.error(f"Error log check error: {e}")

    def _print_summary(self):
        """Print health check summary"""
        logger.info("\n" + "=" * 80)
        logger.info("HEALTH CHECK SUMMARY")
        logger.info("=" * 80)

        # Print passed checks
        if self.checks_passed:
            logger.info("\nPassed Checks:")
            for check in self.checks_passed:
                logger.info(f"  [PASS] {check['check']}: {check['message']}")

        # Print failed checks
        if self.checks_failed:
            logger.info("\nFailed Checks:")
            for check in self.checks_failed:
                status = check['status']
                logger.error(f"  [{status}] {check['check']}: {check['message']}")

        # Overall status
        total = len(self.checks_passed) + len(self.checks_failed)
        logger.info(f"\nOverall: {len(self.checks_passed)}/{total} checks passed")

        if len(self.checks_failed) == 0:
            logger.info("System is HEALTHY")
        else:
            logger.warning("System has ISSUES - review failed checks")

        logger.info("=" * 80)


def main():
    """Main execution"""
    try:
        checker = HealthChecker()
        all_passed = checker.run_all_checks()

        sys.exit(0 if all_passed else 1)

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
