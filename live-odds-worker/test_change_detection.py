#!/usr/bin/env python3
"""
Test script for change detection optimization
Tests that only changed odds trigger database writes
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from live_odds_client import LiveOddsSupabaseClient


def test_change_detection():
    """Test change detection logic"""

    print("=" * 80)
    print("🧪 TESTING CHANGE DETECTION OPTIMIZATION")
    print("=" * 80)
    print()

    # Initialize client
    print("1️⃣ Initializing Supabase client...")
    client = LiveOddsSupabaseClient()
    print("✅ Client initialized\n")

    # Test data - 3 sample odds records
    test_race_id = "test_race_001"
    test_odds = [
        {
            'race_id': test_race_id,
            'horse_id': 'horse_1',
            'bookmaker_id': 'bet365',
            'race_date': '2025-10-09',
            'race_time': '14:30:00',
            'off_dt': '2025-10-09T14:30:00+00:00',
            'course': 'Cheltenham',
            'race_name': 'Test Race',
            'horse_name': 'Test Horse 1',
            'bookmaker_name': 'Bet365',
            'bookmaker_type': 'fixed',
            'odds_decimal': 5.0,
            'odds_fractional': '4/1',
            'odds_timestamp': datetime.now().isoformat()
        },
        {
            'race_id': test_race_id,
            'horse_id': 'horse_2',
            'bookmaker_id': 'williamhill',
            'race_date': '2025-10-09',
            'race_time': '14:30:00',
            'off_dt': '2025-10-09T14:30:00+00:00',
            'course': 'Cheltenham',
            'race_name': 'Test Race',
            'horse_name': 'Test Horse 2',
            'bookmaker_name': 'William Hill',
            'bookmaker_type': 'fixed',
            'odds_decimal': 3.5,
            'odds_fractional': '5/2',
            'odds_timestamp': datetime.now().isoformat()
        },
        {
            'race_id': test_race_id,
            'horse_id': 'horse_3',
            'bookmaker_id': 'paddypower',
            'race_date': '2025-10-09',
            'race_time': '14:30:00',
            'off_dt': '2025-10-09T14:30:00+00:00',
            'course': 'Cheltenham',
            'race_name': 'Test Race',
            'horse_name': 'Test Horse 3',
            'bookmaker_name': 'Paddy Power',
            'bookmaker_type': 'fixed',
            'odds_decimal': 7.0,
            'odds_fractional': '6/1',
            'odds_timestamp': datetime.now().isoformat()
        }
    ]

    # TEST 1: First insert (all new records)
    print("2️⃣ TEST 1: First insert - all records should be NEW")
    print(f"   Inserting {len(test_odds)} odds records...")
    stats1 = client.update_live_odds(test_odds, race_ids=[test_race_id])
    print(f"   ✅ Inserted: {stats1['inserted']}")
    print(f"   ✅ Updated: {stats1['updated']}")
    print(f"   ✅ Skipped: {stats1['skipped']}")
    print(f"   Expected: inserted=3, updated=0, skipped=0")
    assert stats1['inserted'] == 3, f"Expected 3 inserts, got {stats1['inserted']}"
    assert stats1['skipped'] == 0, f"Expected 0 skipped, got {stats1['skipped']}"
    print("   ✅ TEST 1 PASSED\n")

    # TEST 2: Re-insert same odds (no changes)
    print("3️⃣ TEST 2: Re-insert identical odds - all should be SKIPPED")
    print(f"   Sending same {len(test_odds)} odds records...")
    stats2 = client.update_live_odds(test_odds, race_ids=[test_race_id])
    print(f"   ✅ Inserted: {stats2['inserted']}")
    print(f"   ✅ Updated: {stats2['updated']}")
    print(f"   ✅ Skipped: {stats2['skipped']}")
    print(f"   Expected: inserted=0, updated=0, skipped=3")
    assert stats2['skipped'] == 3, f"Expected 3 skipped, got {stats2['skipped']}"
    assert stats2['inserted'] == 0, f"Expected 0 inserts, got {stats2['inserted']}"
    assert stats2['updated'] == 0, f"Expected 0 updates, got {stats2['updated']}"
    print("   ✅ TEST 2 PASSED - Database writes avoided!\n")

    # TEST 3: Change one odds value
    print("4️⃣ TEST 3: Change one odds value - 1 update, 2 skipped")
    test_odds[0]['odds_decimal'] = 6.0  # Change from 5.0 to 6.0
    test_odds[0]['odds_fractional'] = '5/1'
    print(f"   Changed horse_1 odds from 5.0 to 6.0...")
    stats3 = client.update_live_odds(test_odds, race_ids=[test_race_id])
    print(f"   ✅ Inserted: {stats3['inserted']}")
    print(f"   ✅ Updated: {stats3['updated']}")
    print(f"   ✅ Skipped: {stats3['skipped']}")
    print(f"   Expected: inserted=0, updated=1, skipped=2")
    assert stats3['updated'] == 1, f"Expected 1 update, got {stats3['updated']}"
    assert stats3['skipped'] == 2, f"Expected 2 skipped, got {stats3['skipped']}"
    print("   ✅ TEST 3 PASSED - Only changed odds written!\n")

    # Cleanup
    print("5️⃣ Cleaning up test data...")
    try:
        # Delete test race odds
        response = client.client.table('ra_odds_live')\
            .delete()\
            .eq('race_id', test_race_id)\
            .execute()
        deleted = len(response.data) if response.data else 0
        print(f"   ✅ Deleted {deleted} test records\n")
    except Exception as e:
        print(f"   ⚠️  Cleanup failed: {e}\n")

    print("=" * 80)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 80)
    print()
    print("📊 CHANGE DETECTION SUMMARY:")
    print(f"   ✅ Test 1: First insert works correctly (3 new records)")
    print(f"   ✅ Test 2: Identical odds skipped (0 database writes)")
    print(f"   ✅ Test 3: Only changed odds written (1 update, 2 skipped)")
    print()
    print("💰 COST SAVINGS:")
    print(f"   Before optimization: 3 writes every cycle")
    print(f"   After optimization: 0 writes when unchanged (100% reduction)")
    print(f"   With partial changes: 1 write when 1/3 changes (67% reduction)")
    print()
    print("✅ Change detection is working correctly!")
    print()


if __name__ == '__main__':
    try:
        test_change_detection()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
