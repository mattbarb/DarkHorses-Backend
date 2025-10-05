#!/usr/bin/env python3
"""
Statistics update module for automated tracking after fetch cycles

This module is called by cron_live.py and cron_historical.py after each
successful fetch cycle to update statistics and save to JSON.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add odds_statistics directory to path
stats_dir = Path(__file__).parent
sys.path.insert(0, str(stats_dir))

from config import Config
from database import DatabaseConnection
from collectors import HistoricalOddsCollector, LiveOddsCollector
from formatters import JSONFormatter

logger = logging.getLogger('STATISTICS')


def update_statistics(table: str = 'live', save_to_file: bool = True) -> dict:
    """
    Update statistics for the specified table and optionally save to JSON

    Args:
        table: Which table to update ('live' or 'historical')
        save_to_file: Whether to save results to JSON file

    Returns:
        Dictionary containing collected statistics
    """
    try:
        # Initialize database connection
        db = DatabaseConnection(Config.DATABASE_URL)

        # Collect statistics
        stats = {
            'timestamp': datetime.now().isoformat(),
            'table': table
        }

        if table == 'live':
            collector = LiveOddsCollector(db)
            stats['ra_odds_live'] = collector.collect_all_stats()
            logger.info("✅ Live odds statistics updated")

        elif table == 'historical':
            collector = HistoricalOddsCollector(db)
            stats['rb_odds_historical'] = collector.collect_all_stats()
            logger.info("✅ Historical odds statistics updated")

        else:
            logger.error(f"Invalid table: {table}")
            return {}

        # Save to JSON file if requested
        if save_to_file:
            output_dir = Path(Config.DEFAULT_OUTPUT_DIR)
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{table}_stats_latest.json"
            filepath = output_dir / filename

            formatter = JSONFormatter()
            json_output = formatter.format_stats(stats)

            filepath.write_text(json_output)
            logger.info(f"📄 Statistics saved to {filepath}")

        # Clean up
        db.disconnect()

        return stats

    except Exception as e:
        logger.error(f"❌ Error updating statistics: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


def update_all_statistics(save_to_file: bool = True) -> dict:
    """
    Update statistics for both tables

    Args:
        save_to_file: Whether to save results to JSON file

    Returns:
        Dictionary containing statistics for both tables
    """
    try:
        logger.info("📍 Starting statistics collection...")
        logger.info(f"📍 DATABASE_URL configured: {bool(Config.DATABASE_URL)}")

        if not Config.DATABASE_URL:
            logger.error("❌ DATABASE_URL not set - cannot collect statistics")
            return {}

        # Check if using direct db.*.supabase.co URL (won't work on Render due to IPv6-only)
        if 'db.' in Config.DATABASE_URL and '.supabase.co' in Config.DATABASE_URL:
            logger.error("❌ DATABASE_URL uses direct database connection (db.*.supabase.co)")
            logger.error("⚠️  Render doesn't support IPv6, and Supabase db hosts are IPv6-only")
            logger.error("✅ SOLUTION: Use Supabase connection pooler URL instead:")
            logger.error("   Change DATABASE_URL to use: pooler.supabase.com (has IPv4 support)")
            logger.error("   Example: postgresql://...@aws-0-us-west-1.pooler.supabase.com:5432/...")
            return {}

        logger.info("📍 Connecting to database...")
        db = DatabaseConnection(Config.DATABASE_URL)
        logger.info("✅ Database connection established")

        stats = {
            'timestamp': datetime.now().isoformat(),
        }

        # Collect both tables
        logger.info("📍 Collecting historical odds statistics...")
        historical_collector = HistoricalOddsCollector(db)
        stats['rb_odds_historical'] = historical_collector.collect_all_stats()
        logger.info(f"✅ Historical stats collected: {len(stats['rb_odds_historical'])} keys")

        logger.info("📍 Collecting live odds statistics...")
        live_collector = LiveOddsCollector(db)
        stats['ra_odds_live'] = live_collector.collect_all_stats()
        logger.info(f"✅ Live stats collected: {len(stats['ra_odds_live'])} keys")

        logger.info("✅ All statistics collected successfully")

        # Save to JSON file if requested
        if save_to_file:
            output_dir = Path(Config.DEFAULT_OUTPUT_DIR)
            logger.info(f"📍 Creating output directory: {output_dir}")
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Output directory ready: {output_dir}")

            filename = f"all_stats_latest.json"
            filepath = output_dir / filename

            logger.info("📍 Formatting statistics as JSON...")
            formatter = JSONFormatter()
            json_output = formatter.format_stats(stats)

            logger.info(f"📍 Writing to file: {filepath}")
            filepath.write_text(json_output)
            logger.info(f"📄 Statistics saved to {filepath} ({len(json_output)} bytes)")

        db.disconnect()
        logger.info("✅ Database connection closed")

        return stats

    except Exception as e:
        logger.error(f"❌ Error updating all statistics: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


if __name__ == '__main__':
    """Allow running as standalone script"""
    import argparse

    parser = argparse.ArgumentParser(description='Update odds statistics')
    parser.add_argument('--table', choices=['live', 'historical', 'all'], default='all',
                       help='Which table to update (default: all)')
    parser.add_argument('--no-save', action='store_true',
                       help='Do not save to file')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.table == 'all':
        update_all_statistics(save_to_file=not args.no_save)
    else:
        update_statistics(table=args.table, save_to_file=not args.no_save)
