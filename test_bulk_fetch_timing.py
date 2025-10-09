#!/usr/bin/env python3
"""
Test script to measure bulk fetch timing and identify the hang cause
"""

import os
import sys
import time
from datetime import datetime

# Add live-odds-worker to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'live-odds-worker'))

# Set credentials
os.environ['SUPABASE_URL'] = 'https://amsjvmlaknvnppxsgpfk.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFtc2p2bWxha252bnBweHNncGZrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDAxNjQxNSwiZXhwIjoyMDY1NTkyNDE1fQ.8JiQWlaTBH18o8PvElYC5aBAKGw8cfdMBe8KbXTAukI'

from supabase import create_client

print('=' * 80)
print('DATABASE SIZE AND TIMING ANALYSIS')
print('=' * 80)
print()

client = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_SERVICE_KEY']
)

today = datetime.now().date().isoformat()
print(f'Today: {today}')
print()

# Test 1: Count total rows
print('TEST 1: Table size')
print('-' * 80)
try:
    result = client.table('ra_odds_live').select('race_id', count='exact').execute()
    total_rows = result.count
    print(f'✓ Total rows in ra_odds_live: {total_rows:,}')
except Exception as e:
    print(f'✗ Error counting rows: {e}')

print()

# Test 2: Count today's rows
print('TEST 2: Today\'s data size')
print('-' * 80)
try:
    result = client.table('ra_odds_live').select('race_id', count='exact').eq('race_date', today).execute()
    today_rows = result.count
    print(f'✓ Rows for today: {today_rows:,}')

    # Get unique races
    result = client.table('ra_odds_live').select('race_id').eq('race_date', today).execute()
    unique_races = len(set(row['race_id'] for row in result.data)) if result.data else 0
    print(f'✓ Unique races today: {unique_races}')

    if unique_races > 0:
        avg_per_race = today_rows / unique_races
        print(f'✓ Average rows per race: {avg_per_race:.0f}')
        print()
        if today_rows > 50000:
            print(f'⚠️  WARNING: {today_rows:,} rows is a LARGE dataset!')
            print(f'   Bulk fetching this many rows will cause delays')
except Exception as e:
    print(f'✗ Error analyzing today\'s data: {e}')

print()

# Test 3: Timing bulk fetch (what change detection does)
print('TEST 3: Bulk fetch timing (simulating change detection)')
print('-' * 80)
try:
    # Get race IDs for today
    result = client.table('ra_odds_live').select('race_id').eq('race_date', today).limit(1000).execute()
    race_ids = list(set(row['race_id'] for row in result.data)) if result.data else []
    print(f'Found {len(race_ids)} race IDs to test with')
    print()

    if len(race_ids) >= 3:
        # Test with 3 races (typical fetch cycle)
        print('Scenario 1: Fetch 3 races (typical cycle)')
        start = time.time()
        result = client.table('ra_odds_live').select('race_id,horse_id,bookmaker_id,odds_decimal').in_('race_id', race_ids[:3]).execute()
        elapsed = time.time() - start
        rows = len(result.data) if result.data else 0
        print(f'  Time: {elapsed:.2f}s')
        print(f'  Rows: {rows:,}')
        print(f'  Status: {"✓ FAST" if elapsed < 1 else "⚠️  SLOW"}')
        print()

    if len(race_ids) >= 10:
        # Test with 10 races
        print('Scenario 2: Fetch 10 races')
        start = time.time()
        result = client.table('ra_odds_live').select('race_id,horse_id,bookmaker_id,odds_decimal').in_('race_id', race_ids[:10]).execute()
        elapsed = time.time() - start
        rows = len(result.data) if result.data else 0
        print(f'  Time: {elapsed:.2f}s')
        print(f'  Rows: {rows:,}')
        print(f'  Status: {"✓ OK" if elapsed < 2 else "⚠️  SLOW"}')
        print()

    if len(race_ids) > 10:
        # Test with ALL races (current implementation)
        print(f'Scenario 3: Fetch ALL {len(race_ids)} races (CURRENT IMPLEMENTATION)')
        start = time.time()
        result = client.table('ra_odds_live').select('race_id,horse_id,bookmaker_id,odds_decimal').in_('race_id', race_ids).execute()
        elapsed = time.time() - start
        rows = len(result.data) if result.data else 0
        print(f'  Time: {elapsed:.2f}s')
        print(f'  Rows: {rows:,}')
        print(f'  Status: {"✓ OK" if elapsed < 3 else "❌ TOO SLOW - CAUSING HANGS"}')
        print()

        if elapsed > 5:
            print('🔥 ROOT CAUSE IDENTIFIED:')
            print(f'   - Bulk fetch takes {elapsed:.2f}s for {rows:,} rows')
            print(f'   - This blocks concurrent frontend queries')
            print(f'   - Frontend "Updating now..." hangs waiting for this')
            print(f'   - SOLUTION: Only fetch races being updated (not all races)')

except Exception as e:
    print(f'✗ Error in timing test: {e}')
    import traceback
    traceback.print_exc()

print()

# Test 4: Simulate frontend query during backend operation
print('TEST 4: Frontend query simulation')
print('-' * 80)
try:
    # Get a race ID to query
    result = client.table('ra_odds_live').select('race_id').eq('race_date', today).limit(1).execute()
    if result.data:
        test_race_id = result.data[0]['race_id']
        print(f'Testing frontend query for race: {test_race_id}')

        # Simulate frontend loading a race page
        start = time.time()
        result = client.table('ra_odds_live').select('*').eq('race_id', test_race_id).execute()
        elapsed = time.time() - start
        rows = len(result.data) if result.data else 0

        print(f'  Time: {elapsed:.2f}s')
        print(f'  Rows: {rows}')
        print(f'  Status: {"✓ FAST" if elapsed < 1 else "⚠️  SLOW"}')
        print()

        if elapsed > 2:
            print('⚠️  Frontend query is slow - this contributes to "Updating now..." hangs')
    else:
        print('No race data found for today')

except Exception as e:
    print(f'✗ Error in frontend simulation: {e}')

print()
print('=' * 80)
print('ANALYSIS COMPLETE')
print('=' * 80)
