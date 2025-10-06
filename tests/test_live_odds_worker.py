#!/usr/bin/env python3
"""
Test Live Odds Worker
Verifies that live odds data is being collected and stored in ra_odds_live table
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from colorama import Fore, Style, init

# Load environment
env_file = Path(__file__).parent.parent / '.env.local'
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

# Initialize colorama
init(autoreset=True)

class LiveOddsWorkerTest:
    """Test suite for Live Odds Worker"""

    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment")

        self.client = create_client(self.supabase_url, self.supabase_key)
        self.results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }

    def print_header(self):
        """Print test header"""
        print("\n" + "=" * 80)
        print(f"{Fore.CYAN}🏇 LIVE ODDS WORKER TEST{Style.RESET_ALL}")
        print("=" * 80)
        print(f"Testing: ra_odds_live table")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")

    def test_table_exists(self):
        """Test 1: Verify ra_odds_live table exists and has data"""
        print(f"{Fore.YELLOW}[TEST 1]{Style.RESET_ALL} Checking if ra_odds_live table exists...")

        try:
            response = self.client.table('ra_odds_live').select('*', count='exact').limit(1).execute()

            if response.count > 0:
                print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Table exists with {response.count:,} total records")
                self.results['passed'] += 1
                return True
            else:
                print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Table exists but has NO data")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error accessing table: {e}")
            self.results['failed'] += 1
            return False

    def test_recent_data(self):
        """Test 2: Verify data has been updated recently (within last 30 minutes)"""
        print(f"\n{Fore.YELLOW}[TEST 2]{Style.RESET_ALL} Checking for recent updates...")

        try:
            # Check for records updated in last 30 minutes
            cutoff_time = (datetime.now() - timedelta(minutes=30)).isoformat()

            response = self.client.table('ra_odds_live')\
                .select('*', count='exact')\
                .gte('updated_at', cutoff_time)\
                .limit(1)\
                .execute()

            if response.count > 0:
                print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Found {response.count:,} records updated in last 30 minutes")
                self.results['passed'] += 1

                # Show sample record
                if response.data:
                    sample = response.data[0]
                    print(f"  Sample: {sample.get('horse_name')} @ {sample.get('course')}")
                    print(f"          {sample.get('bookmaker_name')} - Odds: {sample.get('odds_decimal')}")
                    print(f"          Updated: {sample.get('updated_at')}")
                return True
            else:
                print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - NO records updated in last 30 minutes")
                print(f"  Worker may not be running or races may have finished")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error checking recent data: {e}")
            self.results['failed'] += 1
            return False

    def test_data_coverage(self):
        """Test 3: Verify data coverage (races, horses, bookmakers)"""
        print(f"\n{Fore.YELLOW}[TEST 3]{Style.RESET_ALL} Checking data coverage...")

        try:
            # Get today's data
            today = datetime.now().date().isoformat()

            response = self.client.table('ra_odds_live')\
                .select('race_id,horse_id,bookmaker_id')\
                .gte('race_date', today)\
                .execute()

            if response.data:
                # Count unique values
                unique_races = len(set(r['race_id'] for r in response.data if r.get('race_id')))
                unique_horses = len(set(r['horse_id'] for r in response.data if r.get('horse_id')))
                unique_bookmakers = len(set(r['bookmaker_id'] for r in response.data if r.get('bookmaker_id')))

                print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Data coverage for today:")
                print(f"  🏁 Unique races: {unique_races}")
                print(f"  🐴 Unique horses: {unique_horses}")
                print(f"  📊 Unique bookmakers: {unique_bookmakers}")

                self.results['passed'] += 1

                # Warnings for low coverage
                if unique_bookmakers < 5:
                    print(f"{Fore.YELLOW}  ⚠️  WARNING: Low bookmaker count (expected 15-26){Style.RESET_ALL}")
                    self.results['warnings'] += 1

                return True
            else:
                print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - No data found for today")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error checking coverage: {e}")
            self.results['failed'] += 1
            return False

    def test_data_quality(self):
        """Test 4: Verify data quality (no nulls in critical fields)"""
        print(f"\n{Fore.YELLOW}[TEST 4]{Style.RESET_ALL} Checking data quality...")

        try:
            # Get recent sample
            response = self.client.table('ra_odds_live')\
                .select('race_id,horse_id,bookmaker_id,odds_decimal,race_date,updated_at')\
                .limit(100)\
                .execute()

            if response.data:
                total = len(response.data)
                missing_race_id = sum(1 for r in response.data if not r.get('race_id'))
                missing_horse_id = sum(1 for r in response.data if not r.get('horse_id'))
                missing_bookmaker = sum(1 for r in response.data if not r.get('bookmaker_id'))
                missing_odds = sum(1 for r in response.data if not r.get('odds_decimal'))

                if missing_race_id == 0 and missing_horse_id == 0 and missing_bookmaker == 0:
                    print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - All critical fields populated in {total} sample records")
                    self.results['passed'] += 1

                    if missing_odds > 0:
                        print(f"{Fore.YELLOW}  ⚠️  {missing_odds} records missing odds (may be expected){Style.RESET_ALL}")
                        self.results['warnings'] += 1

                    return True
                else:
                    print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Found NULL values in critical fields:")
                    if missing_race_id > 0:
                        print(f"  Missing race_id: {missing_race_id}/{total}")
                    if missing_horse_id > 0:
                        print(f"  Missing horse_id: {missing_horse_id}/{total}")
                    if missing_bookmaker > 0:
                        print(f"  Missing bookmaker_id: {missing_bookmaker}/{total}")

                    self.results['failed'] += 1
                    return False
            else:
                print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - No data to check")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error checking quality: {e}")
            self.results['failed'] += 1
            return False

    def test_adaptive_updates(self):
        """Test 5: Verify adaptive scheduling is working (multiple updates per race)"""
        print(f"\n{Fore.YELLOW}[TEST 5]{Style.RESET_ALL} Checking adaptive scheduling...")

        try:
            # Get a race with multiple updates
            response = self.client.table('ra_odds_live')\
                .select('race_id,horse_id,bookmaker_id,updated_at')\
                .order('updated_at', desc=True)\
                .limit(200)\
                .execute()

            if response.data:
                # Group by race to find races with multiple updates
                races = {}
                for record in response.data:
                    race_id = record.get('race_id')
                    updated_at = record.get('updated_at')
                    if race_id and updated_at:
                        if race_id not in races:
                            races[race_id] = []
                        races[race_id].append(updated_at)

                # Find races with multiple distinct update times
                multi_update_races = [
                    (race_id, len(set(times)))
                    for race_id, times in races.items()
                    if len(set(times)) > 1
                ]

                if multi_update_races:
                    max_updates = max(count for _, count in multi_update_races)
                    print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Adaptive scheduling detected")
                    print(f"  Found {len(multi_update_races)} races with multiple updates")
                    print(f"  Max update timestamps for single race: {max_updates}")
                    self.results['passed'] += 1
                    return True
                else:
                    print(f"{Fore.YELLOW}⚠️  WARNING{Style.RESET_ALL} - No races with multiple update timestamps found")
                    print(f"  This could mean: races finished, or only one update cycle ran")
                    self.results['warnings'] += 1
                    return True
            else:
                print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - No data to analyze")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error checking adaptive updates: {e}")
            self.results['failed'] += 1
            return False

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print(f"{Fore.CYAN}TEST SUMMARY - LIVE ODDS WORKER{Style.RESET_ALL}")
        print("=" * 80)

        total = self.results['passed'] + self.results['failed']
        pass_rate = (self.results['passed'] / total * 100) if total > 0 else 0

        print(f"✅ Passed: {Fore.GREEN}{self.results['passed']}{Style.RESET_ALL}")
        print(f"❌ Failed: {Fore.RED}{self.results['failed']}{Style.RESET_ALL}")
        print(f"⚠️  Warnings: {Fore.YELLOW}{self.results['warnings']}{Style.RESET_ALL}")
        print(f"📊 Pass Rate: {pass_rate:.1f}%")

        if self.results['failed'] == 0:
            print(f"\n{Fore.GREEN}🎉 ALL TESTS PASSED - Live Odds Worker is functioning correctly!{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}⚠️  SOME TESTS FAILED - Check worker logs for issues{Style.RESET_ALL}")

        print("=" * 80 + "\n")

        return self.results['failed'] == 0

    def run_all_tests(self):
        """Run all tests"""
        self.print_header()

        self.test_table_exists()
        self.test_recent_data()
        self.test_data_coverage()
        self.test_data_quality()
        self.test_adaptive_updates()

        return self.print_summary()


if __name__ == "__main__":
    test = LiveOddsWorkerTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
