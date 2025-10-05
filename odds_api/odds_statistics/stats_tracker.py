#!/usr/bin/env python3
"""
Odds Data Pipeline Statistics Tracker

Tracks and reports statistics for ra_odds_historical and ra_odds_live tables

Usage:
    python stats_tracker.py                          # Console output for both tables
    python stats_tracker.py --table historical       # Historical table only
    python stats_tracker.py --table live             # Live table only
    python stats_tracker.py --format json            # JSON output
    python stats_tracker.py --format json --output stats.json  # Save to file
"""

import argparse
import sys
import logging
from datetime import datetime
from pathlib import Path

from config import Config
from database import DatabaseConnection
from collectors import HistoricalOddsCollector, LiveOddsCollector
from formatters import ConsoleFormatter, JSONFormatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OddsStatisticsTracker:
    """Main orchestrator for statistics tracking"""

    def __init__(self):
        # Validate configuration
        Config.validate()

        # Initialize database connection
        self.db = DatabaseConnection(Config.DATABASE_URL)

        # Initialize collectors
        self.historical_collector = HistoricalOddsCollector(self.db)
        self.live_collector = LiveOddsCollector(self.db)

        # Initialize formatters
        self.console_formatter = ConsoleFormatter()
        self.json_formatter = JSONFormatter()

    def collect_statistics(self, table: str = 'all'):
        """Collect statistics for specified table(s)"""
        stats = {
            'timestamp': datetime.now().isoformat(),
        }

        if table in ['all', 'historical']:
            logger.info("Collecting ra_odds_historical statistics...")
            try:
                stats['ra_odds_historical'] = self.historical_collector.collect_all_stats()
            except Exception as e:
                logger.error(f"Error collecting historical stats: {e}")
                stats['ra_odds_historical'] = {'error': str(e)}

        if table in ['all', 'live']:
            logger.info("Collecting ra_odds_live statistics...")
            try:
                stats['ra_odds_live'] = self.live_collector.collect_all_stats()
            except Exception as e:
                logger.error(f"Error collecting live stats: {e}")
                stats['ra_odds_live'] = {'error': str(e)}

        return stats

    def generate_report(self, stats: dict, format: str, output_path: str = None):
        """Generate report in specified format"""
        if format == 'console':
            report = self.console_formatter.format_stats(stats)
            print(report)

        elif format == 'json':
            report = self.json_formatter.format_stats(stats)
            if output_path:
                Path(output_path).write_text(report)
                logger.info(f"JSON report saved to {output_path}")
            else:
                print(report)

    def run(self, table: str = 'all', format: str = 'console', output_path: str = None):
        """Main execution method"""
        try:
            # Test database connection
            logger.info("Testing database connection...")
            if not self.db.test_connection():
                logger.error("Database connection failed")
                sys.exit(1)

            # Collect statistics
            stats = self.collect_statistics(table)

            # Generate report
            self.generate_report(stats, format, output_path)

            logger.info("Statistics collection completed successfully")

        except Exception as e:
            logger.error(f"Error during statistics collection: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        finally:
            self.db.disconnect()


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Odds Data Pipeline Statistics Tracker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show all statistics in console
  python stats_tracker.py

  # Show historical table statistics only
  python stats_tracker.py --table historical

  # Show live table statistics only
  python stats_tracker.py --table live

  # Export all statistics to JSON
  python stats_tracker.py --format json --output stats.json

  # Export to JSON and print to console
  python stats_tracker.py --format json
        """
    )

    parser.add_argument(
        '--table',
        choices=['all', 'historical', 'live'],
        default='all',
        help='Which table(s) to analyze (default: all)'
    )

    parser.add_argument(
        '--format',
        choices=['console', 'json'],
        default='console',
        help='Output format (default: console)'
    )

    parser.add_argument(
        '--output',
        help='Output file path (for json format)'
    )

    args = parser.parse_args()

    # Run tracker
    tracker = OddsStatisticsTracker()
    tracker.run(
        table=args.table,
        format=args.format,
        output_path=args.output
    )


if __name__ == '__main__':
    main()
