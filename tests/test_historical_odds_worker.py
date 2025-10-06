#!/usr/bin/env python3
"""
Test Historical Odds Worker
Verifies that historical odds data is being collected and stored in ra_odds_historical table
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

class HistoricalOddsWorkerTest:
    """Test suite for Historical Odds Worker"""

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
        print(f"{Fore.CYAN}📚 HISTORICAL ODDS WORKER TEST{Style.RESET_ALL}")
        print("=" * 80)
        print(f"Testing: ra_odds_historical table")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")

    def test_table_exists(self):
        """Test 1: Verify ra_odds_historical table exists and has data"""
        print(f"{Fore.YELLOW}[TEST 1]{Style.RESET_ALL} Checking if ra_odds_historical table exists...")

        try:
            response = self.client.table('ra_odds_historical').select('*', count='exact').limit(1).execute()

            if response.count > 0:
                print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Table exists with {response.count:,} total records")
                self.results['passed'] += 1
                return True
            else:
                print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Table exists but has NO data")
                print(f"  Historical backfill may not have started yet")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error accessing table: {e}")
            self.results['failed'] += 1
            return False

    def test_date_coverage(self):
        """Test 2: Verify historical data coverage (date range)"""
        print(f"\n{Fore.YELLOW}[TEST 2]{Style.RESET_ALL} Checking date coverage...")

        try:
            # Get earliest and latest dates
            response = self.client.table('ra_odds_historical')\
                .select('race_date')\
                .order('race_date', desc=False)\
                .limit(1)\
                .execute()

            earliest_response = self.client.table('ra_odds_historical')\
                .select('race_date')\
                .order('race_date', desc=True)\
                .limit(1)\
                .execute()

            if response.data and earliest_response.data:
                earliest = response.data[0]['race_date']
                latest = earliest_response.data[0]['race_date']

                # Count unique dates
                dates_response = self.client.table('ra_odds_historical')\
                    .select('race_date')\
                    .execute()

                unique_dates = len(set(r['race_date'] for r in dates_response.data if r.get('race_date')))

                print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Historical data coverage:")
                print(f"  📅 Earliest date: {earliest}")
                print(f"  📅 Latest date: {latest}")
                print(f"  📊 Unique dates covered: {unique_dates:,}")

                self.results['passed'] += 1

                # Check if we have recent data
                yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
                if latest < yesterday:
                    print(f"{Fore.YELLOW}  ⚠️  WARNING: Latest date is not recent (expected yesterday or today){Style.RESET_ALL}")
                    self.results['warnings'] += 1

                return True
            else:
                print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Could not determine date range")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error checking date coverage: {e}")
            self.results['failed'] += 1
            return False

    def test_recent_backfill(self):
        """Test 3: Verify recent backfill activity (data from last 7 days)"""
        print(f"\n{Fore.YELLOW}[TEST 3]{Style.RESET_ALL} Checking recent backfill activity...")

        try:
            # Check for data from last 7 days
            week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()

            response = self.client.table('ra_odds_historical')\
                .select('*', count='exact')\
                .gte('race_date', week_ago)\
                .limit(1)\
                .execute()

            if response.count > 0:
                print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Found {response.count:,} records from last 7 days")
                self.results['passed'] += 1
                return True
            else:
                print(f"{Fore.YELLOW}⚠️  WARNING{Style.RESET_ALL} - No records from last 7 days")
                print(f"  Daily backfill may not have run yet (scheduled for 1:00 AM)")
                self.results['warnings'] += 1
                return True
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error checking recent backfill: {e}")
            self.results['failed'] += 1
            return False

    def test_results_data(self):
        """Test 4: Verify race results are present (finishing positions)"""
        print(f"\n{Fore.YELLOW}[TEST 4]{Style.RESET_ALL} Checking race results data...")

        try:
            # Get sample of recent data
            response = self.client.table('ra_odds_historical')\
                .select('race_id,horse_id,horse_name,finishing_position')\
                .limit(100)\
                .execute()

            if response.data:
                total = len(response.data)
                with_positions = sum(1 for r in response.data if r.get('finishing_position') is not None)

                if with_positions > 0:
                    percentage = (with_positions / total * 100)
                    print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Race results present:")
                    print(f"  🏁 {with_positions}/{total} records have finishing positions ({percentage:.1f}%)")
                    self.results['passed'] += 1

                    # Show sample
                    sample_with_position = next((r for r in response.data if r.get('finishing_position')), None)
                    if sample_with_position:
                        print(f"  Sample: {sample_with_position.get('horse_name')} - Position {sample_with_position.get('finishing_position')}")

                    return True
                else:
                    print(f"{Fore.YELLOW}⚠️  WARNING{Style.RESET_ALL} - No finishing positions found in sample")
                    print(f"  Data may be for future races or results not yet available")
                    self.results['warnings'] += 1
                    return True
            else:
                print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - No data to check")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error checking results: {e}")
            self.results['failed'] += 1
            return False

    def test_data_quality(self):
        """Test 5: Verify data quality (no nulls in critical fields)"""
        print(f"\n{Fore.YELLOW}[TEST 5]{Style.RESET_ALL} Checking data quality...")

        try:
            response = self.client.table('ra_odds_historical')\
                .select('race_id,horse_id,bookmaker_id,odds_decimal,race_date')\
                .limit(100)\
                .execute()

            if response.data:
                total = len(response.data)
                missing_race_id = sum(1 for r in response.data if not r.get('race_id'))
                missing_horse_id = sum(1 for r in response.data if not r.get('horse_id'))
                missing_bookmaker = sum(1 for r in response.data if not r.get('bookmaker_id'))
                missing_date = sum(1 for r in response.data if not r.get('race_date'))

                if missing_race_id == 0 and missing_horse_id == 0 and missing_date == 0:
                    print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - All critical fields populated in {total} sample records")
                    self.results['passed'] += 1

                    if missing_bookmaker > 0:
                        print(f"{Fore.YELLOW}  ⚠️  {missing_bookmaker} records missing bookmaker_id{Style.RESET_ALL}")
                        self.results['warnings'] += 1

                    return True
                else:
                    print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Found NULL values in critical fields:")
                    if missing_race_id > 0:
                        print(f"  Missing race_id: {missing_race_id}/{total}")
                    if missing_horse_id > 0:
                        print(f"  Missing horse_id: {missing_horse_id}/{total}")
                    if missing_date > 0:
                        print(f"  Missing race_date: {missing_date}/{total}")

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

    def test_backfill_progress(self):
        """Test 6: Check backfill progress toward 2015 goal"""
        print(f"\n{Fore.YELLOW}[TEST 6]{Style.RESET_ALL} Checking backfill progress...")

        try:
            # Get earliest date
            response = self.client.table('ra_odds_historical')\
                .select('race_date')\
                .order('race_date', desc=False)\
                .limit(1)\
                .execute()

            if response.data:
                earliest = response.data[0]['race_date']
                target = "2015-01-01"

                print(f"  📅 Current earliest date: {earliest}")
                print(f"  🎯 Target (goal): {target}")

                if earliest <= target:
                    print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Backfill complete to 2015!")
                    self.results['passed'] += 1
                else:
                    # Calculate remaining years
                    from datetime import date
                    earliest_date = date.fromisoformat(earliest)
                    target_date = date.fromisoformat(target)
                    days_remaining = (earliest_date - target_date).days

                    print(f"{Fore.YELLOW}⚠️  IN PROGRESS{Style.RESET_ALL} - Backfill in progress")
                    print(f"  📊 Approximately {days_remaining} days remaining to backfill")
                    self.results['warnings'] += 1

                return True
            else:
                print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Could not determine backfill progress")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error checking backfill: {e}")
            self.results['failed'] += 1
            return False

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print(f"{Fore.CYAN}TEST SUMMARY - HISTORICAL ODDS WORKER{Style.RESET_ALL}")
        print("=" * 80)

        total = self.results['passed'] + self.results['failed']
        pass_rate = (self.results['passed'] / total * 100) if total > 0 else 0

        print(f"✅ Passed: {Fore.GREEN}{self.results['passed']}{Style.RESET_ALL}")
        print(f"❌ Failed: {Fore.RED}{self.results['failed']}{Style.RESET_ALL}")
        print(f"⚠️  Warnings: {Fore.YELLOW}{self.results['warnings']}{Style.RESET_ALL}")
        print(f"📊 Pass Rate: {pass_rate:.1f}%")

        if self.results['failed'] == 0:
            print(f"\n{Fore.GREEN}🎉 ALL TESTS PASSED - Historical Odds Worker is functioning correctly!{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}⚠️  SOME TESTS FAILED - Check worker logs for issues{Style.RESET_ALL}")

        print("=" * 80 + "\n")

        return self.results['failed'] == 0

    def run_all_tests(self):
        """Run all tests"""
        self.print_header()

        self.test_table_exists()
        self.test_date_coverage()
        self.test_recent_backfill()
        self.test_results_data()
        self.test_data_quality()
        self.test_backfill_progress()

        return self.print_summary()


if __name__ == "__main__":
    test = HistoricalOddsWorkerTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
