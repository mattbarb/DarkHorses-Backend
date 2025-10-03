#!/usr/bin/env python3
"""
Test Mode - Single Record Validation
Tests Supabase connection and inserts ONE test record for live_odds
Use this to verify deployment before running full production service
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    print("ℹ️ No .env file - using Render.com environment variables")

# Setup logging with detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def test_supabase_connection():
    """Test 1: Verify Supabase connection"""
    print("\n" + "="*70)
    print("TEST 1: SUPABASE CONNECTION")
    print("="*70)

    try:
        from live_odds_client import LiveOddsSupabaseClient

        logger.info("🔌 Connecting to Supabase...")
        client = LiveOddsSupabaseClient()

        logger.info(f"✅ Connected to: {os.getenv('SUPABASE_URL')}")
        logger.info("✅ Database connection verified")

        return client

    except Exception as e:
        logger.error(f"❌ CONNECTION FAILED: {e}")
        logger.error(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
        logger.error(f"SUPABASE_SERVICE_KEY: {'SET' if os.getenv('SUPABASE_SERVICE_KEY') else 'NOT SET'}")
        return None

def test_single_insert(client):
    """Test 2: Insert a single test record"""
    print("\n" + "="*70)
    print("TEST 2: SINGLE RECORD INSERT")
    print("="*70)

    test_record = {
        'race_id': f'test_race_{int(datetime.now().timestamp())}',
        'horse_id': f'test_horse_{int(datetime.now().timestamp())}',
        'bookmaker_id': 'betfair',
        'race_date': datetime.now().date().isoformat(),
        'race_time': '14:30',
        'course': 'TEST_TRACK',
        'race_name': 'Test Stakes',
        'horse_name': 'Test Horse',
        'bookmaker_name': 'Betfair',
        'bookmaker_type': 'exchange',
        'odds_decimal': 3.50,
        'back_price': 3.50,
        'lay_price': 3.55,
        'odds_timestamp': datetime.now().isoformat(),
        'market_status': 'OPEN'
    }

    try:
        logger.info("📝 Preparing test record...")
        logger.info(f"   Race ID: {test_record['race_id']}")
        logger.info(f"   Horse: {test_record['horse_name']}")
        logger.info(f"   Bookmaker: {test_record['bookmaker_name']}")

        logger.info("💾 Inserting into Supabase...")
        response = client.client.table('ra_odds_live').insert(test_record).execute()

        if response.data:
            logger.info("✅ TEST RECORD INSERTED SUCCESSFULLY!")
            logger.info(f"   Inserted ID: {response.data[0].get('id', 'N/A')}")
            logger.info(f"   Race ID: {response.data[0].get('race_id')}")
            logger.info(f"   Timestamp: {response.data[0].get('fetched_at')}")

            # Verify we can read it back
            logger.info("\n🔍 Verifying record can be read back...")
            verify_response = client.client.table('ra_odds_live')\
                .select('*')\
                .eq('race_id', test_record['race_id'])\
                .execute()

            if verify_response.data:
                logger.info("✅ TEST RECORD VERIFIED - Can read from database")
                logger.info(f"   Found {len(verify_response.data)} record(s)")

            # Clean up test record
            logger.info("\n🧹 Cleaning up test record...")
            client.client.table('ra_odds_live')\
                .delete()\
                .eq('race_id', test_record['race_id'])\
                .execute()
            logger.info("✅ Test record cleaned up")

            return True
        else:
            logger.error("❌ INSERT FAILED - No data returned")
            return False

    except Exception as e:
        logger.error(f"❌ INSERT FAILED: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_racing_api():
    """Test 3: Verify Racing API connection"""
    print("\n" + "="*70)
    print("TEST 3: RACING API CONNECTION")
    print("="*70)

    try:
        import requests
        from datetime import datetime, timedelta

        username = os.getenv('RACING_API_USERNAME')
        password = os.getenv('RACING_API_PASSWORD')

        if not username or not password:
            logger.error("❌ Racing API credentials not set")
            return False

        logger.info("🔌 Testing Racing API connection...")

        url = "https://api.theracingapi.com/v1/racecards/pro"
        today = datetime.now().strftime('%Y-%m-%d')

        response = requests.get(
            url,
            params={'date': today, 'region_codes': 'gb'},
            auth=(username, password),
            timeout=10
        )

        if response.status_code in [200, 404]:
            logger.info("✅ Racing API authentication successful")
            if response.status_code == 200:
                data = response.json()
                races = data.get('racecards', [])
                logger.info(f"   Found {len(races)} races for today")
            else:
                logger.info("   No races found today (404 - this is normal)")
            return True
        else:
            logger.error(f"❌ Racing API returned status: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ Racing API test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 LIVE ODDS SERVICE - DEPLOYMENT TEST")
    print("="*70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print("="*70)

    results = {
        'supabase_connection': False,
        'single_insert': False,
        'racing_api': False
    }

    # Test 1: Supabase Connection
    client = test_supabase_connection()
    results['supabase_connection'] = client is not None

    # Test 2: Single Insert (only if connection worked)
    if client:
        results['single_insert'] = test_single_insert(client)

    # Test 3: Racing API
    results['racing_api'] = test_racing_api()

    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")

    all_passed = all(results.values())

    print("\n" + "="*70)
    if all_passed:
        print("🎉 ALL TESTS PASSED - READY FOR PRODUCTION")
        print("="*70)
        print("\nYou can now run the full production service:")
        print("  python3 cron_live.py")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - FIX BEFORE DEPLOYING")
        print("="*70)
        print("\nFailed tests must be fixed before production deployment.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
