#!/usr/bin/env python3
"""
Test Mode - Single Record Validation
Tests Supabase connection and inserts ONE test record for historical_odds
Use this to verify deployment before running full production service
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

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
        from historical_odds_client import HistoricalOddsClient

        logger.info("🔌 Connecting to Supabase...")
        client = HistoricalOddsClient()

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

    # Create test record matching rb_odds_historical schema
    test_record = {
        'date_of_race': (datetime.now() - timedelta(days=1)).isoformat(),
        'country': 'GB',
        'track': 'TEST_TRACK',
        'race_time': '14:30:00',
        'horse_name': 'Test Horse',
        'jockey': 'Test Jockey',
        'trainer': 'Test Trainer',
        'industry_sp': 3.50,
        'betfair_sp': 3.45,
        'finishing_position': '1',
        'data_source': 'test_deployment',
        'file_source': 'test_validation',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

    try:
        logger.info("📝 Preparing test record...")
        logger.info(f"   Track: {test_record['track']}")
        logger.info(f"   Horse: {test_record['horse_name']}")
        logger.info(f"   Date: {test_record['date_of_race']}")

        logger.info("💾 Inserting into Supabase...")
        response = client.client.table('rb_odds_historical').insert(test_record).execute()

        if response.data:
            logger.info("✅ TEST RECORD INSERTED SUCCESSFULLY!")
            logger.info(f"   Inserted ID: {response.data[0].get('racing_bet_data_id', 'N/A')}")
            logger.info(f"   Track: {response.data[0].get('track')}")
            logger.info(f"   Created at: {response.data[0].get('created_at')}")

            # Verify we can read it back
            logger.info("\n🔍 Verifying record can be read back...")
            verify_response = client.client.table('rb_odds_historical')\
                .select('*')\
                .eq('track', 'TEST_TRACK')\
                .eq('data_source', 'test_deployment')\
                .execute()

            if verify_response.data:
                logger.info("✅ TEST RECORD VERIFIED - Can read from database")
                logger.info(f"   Found {len(verify_response.data)} record(s)")

            # Clean up test record
            logger.info("\n🧹 Cleaning up test record...")
            client.client.table('rb_odds_historical')\
                .delete()\
                .eq('track', 'TEST_TRACK')\
                .eq('data_source', 'test_deployment')\
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

        username = os.getenv('RACING_API_USERNAME')
        password = os.getenv('RACING_API_PASSWORD')

        if not username or not password:
            logger.error("❌ Racing API credentials not set")
            return False

        logger.info("🔌 Testing Racing API connection...")

        # Test with a past date that should have data
        test_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        url = "https://api.theracingapi.com/v1/racecards/pro"
        response = requests.get(
            url,
            params={'date': test_date, 'region_codes': 'gb'},
            auth=(username, password),
            timeout=10
        )

        if response.status_code in [200, 404]:
            logger.info("✅ Racing API authentication successful")
            if response.status_code == 200:
                data = response.json()
                races = data.get('racecards', [])
                logger.info(f"   Found {len(races)} races for {test_date}")
            else:
                logger.info("   No races found (404 - trying different date)")
            return True
        else:
            logger.error(f"❌ Racing API returned status: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ Racing API test failed: {e}")
        return False

def test_schema_mapping():
    """Test 4: Verify schema mapping works"""
    print("\n" + "="*70)
    print("TEST 4: SCHEMA MAPPING")
    print("="*70)

    try:
        from schema_mapping import SchemaMapper

        logger.info("📋 Testing schema mapper...")
        mapper = SchemaMapper()

        # Test mapping a sample race
        sample_race = {
            'race_id': 'test_123',
            'date': '2024-10-01',
            'course': 'Ascot',
            'off_time': '14:30',
            'race_name': 'Test Stakes',
            'distance': '1m 4f',
            'going': 'Good'
        }

        sample_horse = {
            'horse_id': 'hrs_456',
            'name': 'Test Horse',
            'number': 1,
            'jockey': 'J Smith',
            'trainer': 'T Jones'
        }

        mapped = mapper.map_race_data(sample_race, sample_horse, {'SP': '3/1'})

        if mapped and 'track' in mapped and 'horse_name' in mapped:
            logger.info("✅ Schema mapping successful")
            logger.info(f"   Mapped fields: {len(mapped)} fields")
            return True
        else:
            logger.error("❌ Schema mapping failed - missing fields")
            return False

    except Exception as e:
        logger.error(f"❌ Schema mapping test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 HISTORICAL ODDS SERVICE - DEPLOYMENT TEST")
    print("="*70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print("="*70)

    results = {
        'supabase_connection': False,
        'single_insert': False,
        'racing_api': False,
        'schema_mapping': False
    }

    # Test 1: Supabase Connection
    client = test_supabase_connection()
    results['supabase_connection'] = client is not None

    # Test 2: Single Insert (only if connection worked)
    if client:
        results['single_insert'] = test_single_insert(client)

    # Test 3: Racing API
    results['racing_api'] = test_racing_api()

    # Test 4: Schema Mapping
    results['schema_mapping'] = test_schema_mapping()

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
        print("  python3 cron_historical.py")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - FIX BEFORE DEPLOYING")
        print("="*70)
        print("\nFailed tests must be fixed before production deployment.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
