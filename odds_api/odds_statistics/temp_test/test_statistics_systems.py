#!/usr/bin/env python3
"""
Test script to understand and verify both statistics systems

TWO SEPARATE STATISTICS SYSTEMS:
1. Fetch Metrics (ra_odds_statistics table) - Logs each fetch operation
2. Analytical Statistics (JSON files) - Aggregated analytics from all data
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

print("=" * 80)
print("DARHORSES STATISTICS SYSTEMS TEST")
print("=" * 80)

# ============================================================================
# SYSTEM 1: Fetch Metrics (ra_odds_statistics table)
# ============================================================================

print("\n📊 SYSTEM 1: Fetch Metrics (ra_odds_statistics table)")
print("-" * 80)

print("""
PURPOSE: Logs each individual fetch operation
TABLE: ra_odds_statistics
WRITTEN BY: live_odds_client.py (line 421)
FREQUENCY: After every live odds fetch cycle

STORES:
- fetch_timestamp: When the fetch happened
- races_count: Number of races in THIS fetch
- horses_count: Number of horses in THIS fetch
- bookmakers_found: Number of bookmakers in THIS fetch
- total_odds_fetched: Total odds fetched in THIS operation
- bookmaker_list: Array of bookmaker IDs found
- fetch_duration_ms: How long the fetch took
- errors_count: Errors in THIS fetch

DOES NOT STORE:
- Total records across all time
- Unique entity counts (races, horses, bookmakers)
- Data quality metrics
- Distribution analysis
- Coverage statistics
""")

# Check if we can query the table
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / '.env.local')

    from supabase import create_client

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

    if supabase_url and supabase_key:
        print("✅ Supabase credentials found - Testing connection...")
        client = create_client(supabase_url, supabase_key)

        # Query recent fetch metrics
        result = client.table('ra_odds_statistics')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()

        print(f"✅ Connected! Found {len(result.data)} recent fetch operations")

        if result.data:
            print("\nMost recent fetch:")
            latest = result.data[0]
            print(f"  Timestamp: {latest.get('fetch_timestamp')}")
            print(f"  Races: {latest.get('races_count')}")
            print(f"  Horses: {latest.get('horses_count')}")
            print(f"  Bookmakers: {latest.get('bookmakers_found')}")
            print(f"  Total Odds: {latest.get('total_odds_fetched')}")
            print(f"  Duration: {latest.get('fetch_duration_ms')}ms")
        else:
            print("⚠️  No fetch metrics found in table (scheduler may not have run yet)")
    else:
        print("⚠️  SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
        print("   Cannot test fetch metrics table connection")

except Exception as e:
    print(f"❌ Error testing fetch metrics: {e}")

# ============================================================================
# SYSTEM 2: Analytical Statistics (JSON files)
# ============================================================================

print("\n\n📈 SYSTEM 2: Analytical Statistics (JSON files)")
print("-" * 80)

print("""
PURPOSE: Calculate and cache aggregated analytics
OUTPUT: JSON files in odds_statistics/output/
CALCULATED BY: odds_statistics/update_stats.py
FREQUENCY: Every 10 minutes (scheduler) + after fetch cycles

CALCULATES:
- Total records across ALL time
- Unique counts (DISTINCT races, horses, bookmakers, courses)
- Date ranges (earliest/latest)
- Recent activity (last hour, 24h, 7d)
- Data quality metrics (NULL counts)
- Bookmaker coverage analysis
- Distribution by date, course, country
- Market status breakdown (OPEN/CLOSED)

SOURCE DATA:
- Queries ra_odds_live table (live odds)
- Queries rb_odds_historical table (historical odds)
- Uses direct PostgreSQL connection (not Supabase SDK)
- Runs complex aggregations (COUNT DISTINCT, GROUP BY, etc.)

OUTPUT FILES:
- live_stats_latest.json
- historical_stats_latest.json
- all_stats_latest.json
""")

# Check configuration
try:
    from config import Config

    print("Configuration Check:")
    print(f"  DATABASE_URL set: {bool(Config.DATABASE_URL)}")
    print(f"  Output directory: {Config.DEFAULT_OUTPUT_DIR}")

    output_path = Path(Config.DEFAULT_OUTPUT_DIR)
    print(f"  Directory exists: {output_path.exists()}")

    if output_path.exists():
        files = list(output_path.glob('*.json'))
        print(f"  JSON files found: {len(files)}")
        for f in files:
            size = f.stat().st_size
            print(f"    - {f.name} ({size} bytes)")

    if Config.DATABASE_URL:
        if 'db.' in Config.DATABASE_URL and '.supabase.co' in Config.DATABASE_URL:
            print("\n⚠️  WARNING: DATABASE_URL uses direct db.*.supabase.co connection")
            print("   This is IPv6-only and WILL NOT WORK on Render.com")
            print("   ✅ SOLUTION: Use pooler.supabase.com instead")
        else:
            print("\n✅ DATABASE_URL appears correctly configured")
    else:
        print("\n⚠️  DATABASE_URL not set")
        print("   Analytical statistics cannot be calculated")
        print("   Set in .env.local for local testing")

except Exception as e:
    print(f"❌ Error checking configuration: {e}")

# ============================================================================
# TEST ANALYTICAL STATISTICS COLLECTION
# ============================================================================

print("\n\n🧪 TEST: Analytical Statistics Collection")
print("-" * 80)

if not Config.DATABASE_URL:
    print("⏭️  Skipping - DATABASE_URL not set")
else:
    print("Attempting to collect statistics...")

    try:
        from update_stats import update_all_statistics

        print("Calling update_all_statistics()...")
        result = update_all_statistics(save_to_file=True)

        if result:
            print(f"✅ Statistics collected successfully!")
            print(f"   Keys in result: {list(result.keys())}")

            if 'ra_odds_live' in result:
                live_stats = result['ra_odds_live']
                print(f"\n   Live Odds Stats:")
                if 'basic_metrics' in live_stats:
                    basic = live_stats['basic_metrics']
                    print(f"     Total records: {basic.get('total_records', 'N/A')}")
                    print(f"     Unique races: {basic.get('unique_races', 'N/A')}")
                    print(f"     Unique horses: {basic.get('unique_horses', 'N/A')}")

            # Check if files were created
            output_path = Path(Config.DEFAULT_OUTPUT_DIR)
            if output_path.exists():
                files = list(output_path.glob('*.json'))
                print(f"\n   ✅ Created {len(files)} JSON files:")
                for f in files:
                    print(f"      - {f.name} ({f.stat().st_size} bytes)")
        else:
            print("❌ Statistics collection returned empty result")
            print("   Check logs above for errors")

    except Exception as e:
        print(f"❌ Error collecting statistics: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# SUMMARY
# ============================================================================

print("\n\n📋 SUMMARY")
print("=" * 80)

print("""
TWO SEPARATE SYSTEMS FOR DIFFERENT PURPOSES:

1️⃣  FETCH METRICS (ra_odds_statistics table)
   ✓ Purpose: Log each fetch operation
   ✓ Frequency: After every live odds fetch
   ✓ Access: Query ra_odds_statistics table in Supabase
   ✓ Use case: Monitor fetch performance, debug issues

2️⃣  ANALYTICAL STATISTICS (JSON files)
   ✓ Purpose: Aggregated analytics across all data
   ✓ Frequency: Every 10 min + after fetches
   ✓ Access: GET /api/statistics endpoint
   ✓ Use case: Dashboard metrics, analytics, reporting

COMMON ISSUES:

❌ "Statistics not showing on dashboard"
   → Check: JSON files exist in odds_statistics/output/
   → Check: DATABASE_URL is set (needed for calculation)
   → Check: DATABASE_URL uses pooler.supabase.com (not db.*.supabase.co)

❌ "ra_odds_statistics table empty"
   → Check: Live odds scheduler is running
   → Check: Fetch cycles completing successfully
   → This is fetch operation logging, not analytics

❌ "Statistics returning empty on Render"
   → Check: DATABASE_URL uses pooler URL (IPv4 compatible)
   → Check: output/ directory exists (should auto-create)
   → Check: scheduler logs for errors
""")

print("\n✅ Test complete!")
print("=" * 80)
