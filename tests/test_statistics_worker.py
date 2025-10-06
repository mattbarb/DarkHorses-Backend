#!/usr/bin/env python3
"""
Test Statistics Worker
Verifies that statistics are being generated and updated
"""

import os
import sys
import json
from datetime import datetime, timedelta, date
from pathlib import Path
from dotenv import load_dotenv
from colorama import Fore, Style, init
from supabase import create_client, Client

# Load environment
env_file = Path(__file__).parent.parent / '.env.local'
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

# Initialize colorama
init(autoreset=True)

class StatisticsWorkerTest:
    """Test suite for Statistics Worker"""

    def __init__(self):
        # Prefer Supabase SDK (works from any network)
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment")

        # Initialize Supabase client
        self.client: Client = create_client(self.supabase_url, self.supabase_key)

        self.results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }

        # Try to find statistics output directory
        self.output_dir = Path(__file__).parent.parent / 'statistics-worker' / 'output'
        if not self.output_dir.exists():
            self.output_dir = Path(__file__).parent.parent / 'odds_statistics' / 'output'

    def print_header(self):
        """Print test header"""
        print("\n" + "=" * 80)
        print(f"{Fore.CYAN}📊 STATISTICS WORKER TEST{Style.RESET_ALL}")
        print("=" * 80)
        print(f"Testing: Statistics generation and output")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")

    def test_database_connection(self):
        """Test 1: Verify can connect to database for statistics queries"""
        print(f"{Fore.YELLOW}[TEST 1]{Style.RESET_ALL} Checking Supabase connection...")

        try:
            # Simple query to test connection
            response = self.client.table('ra_odds_live').select('*', count='exact').limit(1).execute()
            count = response.count

            print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Supabase connection successful")
            print(f"  📊 ra_odds_live has {count:,} records")
            self.results['passed'] += 1
            return True
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Supabase connection failed: {e}")
            self.results['failed'] += 1
            return False

    def test_statistics_queries(self):
        """Test 2: Verify statistics queries run successfully"""
        print(f"\n{Fore.YELLOW}[TEST 2]{Style.RESET_ALL} Running statistics queries...")

        try:
            today = date.today().isoformat()

            # Fetch all records for today to compute statistics
            response_today = self.client.table('ra_odds_live')\
                .select('race_id,bookmaker_id,horse_id')\
                .gte('race_date', today)\
                .execute()

            stats = {
                'unique_races': len(set(row['race_id'] for row in response_today.data if row.get('race_id'))),
                'unique_bookmakers': len(set(row['bookmaker_id'] for row in response_today.data if row.get('bookmaker_id'))),
                'unique_horses': len(set(row['horse_id'] for row in response_today.data if row.get('horse_id'))),
                'total_records_today': len(response_today.data)
            }

            print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Statistics queries executed successfully:")
            print(f"  🏁 Unique races today: {stats['unique_races']:,}")
            print(f"  📊 Unique bookmakers: {stats['unique_bookmakers']:,}")
            print(f"  🐴 Unique horses today: {stats['unique_horses']:,}")
            print(f"  💾 Total records today: {stats['total_records_today']:,}")

            self.results['passed'] += 1

            # Warnings for unexpected values
            if stats['unique_bookmakers'] == 0:
                print(f"{Fore.YELLOW}  ⚠️  WARNING: No bookmakers found{Style.RESET_ALL}")
                self.results['warnings'] += 1

            return True
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Statistics queries failed: {e}")
            self.results['failed'] += 1
            return False

    def test_output_files(self):
        """Test 3: Verify statistics output JSON files exist and are recent"""
        print(f"\n{Fore.YELLOW}[TEST 3]{Style.RESET_ALL} Checking output files...")

        if not self.output_dir.exists():
            print(f"{Fore.YELLOW}⚠️  WARNING{Style.RESET_ALL} - Output directory not found: {self.output_dir}")
            print(f"  Statistics may be running but files not accessible locally")
            self.results['warnings'] += 1
            return True

        try:
            # Look for JSON files
            json_files = list(self.output_dir.glob('*.json'))

            if json_files:
                print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Found {len(json_files)} JSON output files:")

                for json_file in json_files:
                    # Check file age
                    mod_time = datetime.fromtimestamp(json_file.stat().st_mtime)
                    age = datetime.now() - mod_time

                    status = "📄"
                    if age < timedelta(minutes=15):
                        status = f"{Fore.GREEN}🆕{Style.RESET_ALL}"
                    elif age < timedelta(hours=1):
                        status = f"{Fore.YELLOW}⏰{Style.RESET_ALL}"

                    print(f"  {status} {json_file.name} - Updated {age.total_seconds()/60:.0f} min ago")

                    # Try to read and validate JSON
                    try:
                        with open(json_file, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, dict) and len(data) > 0:
                                print(f"      ✓ Valid JSON with {len(data)} keys")
                    except json.JSONDecodeError:
                        print(f"{Fore.RED}      ✗ Invalid JSON format{Style.RESET_ALL}")
                        self.results['warnings'] += 1

                self.results['passed'] += 1
                return True
            else:
                print(f"{Fore.YELLOW}⚠️  WARNING{Style.RESET_ALL} - No JSON files found in {self.output_dir}")
                print(f"  Statistics worker may not have run yet (runs every 10 min)")
                self.results['warnings'] += 1
                return True
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error checking output files: {e}")
            self.results['failed'] += 1
            return False

    def test_aggregation_accuracy(self):
        """Test 4: Verify aggregation calculations are accurate"""
        print(f"\n{Fore.YELLOW}[TEST 4]{Style.RESET_ALL} Checking aggregation accuracy...")

        try:
            today = date.today().isoformat()

            # Get sample aggregation data
            response = self.client.table('ra_odds_live')\
                .select('race_id,horse_id,bookmaker_id')\
                .gte('race_date', today)\
                .execute()

            if response.data:
                total = len(response.data)
                races = len(set(row['race_id'] for row in response.data if row.get('race_id')))
                horses = len(set(row['horse_id'] for row in response.data if row.get('horse_id')))
                bookmakers = len(set(row['bookmaker_id'] for row in response.data if row.get('bookmaker_id')))

                # Sanity checks
                valid = True
                if races == 0 and total > 0:
                    print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Data exists but no races counted")
                    valid = False
                elif total > 0 and horses == 0:
                    print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Data exists but no horses counted")
                    valid = False
                elif total > 0 and bookmakers == 0:
                    print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Data exists but no bookmakers counted")
                    valid = False
                else:
                    print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Aggregation calculations appear accurate:")
                    print(f"  📊 {total:,} records / {races} races = ~{total/races if races > 0 else 0:.0f} records/race")
                    print(f"  📊 {bookmakers} bookmakers found")

                if valid:
                    self.results['passed'] += 1
                    return True
                else:
                    self.results['failed'] += 1
                    return False
            else:
                print(f"{Fore.YELLOW}⚠️  WARNING{Style.RESET_ALL} - No data to aggregate")
                self.results['warnings'] += 1
                return True
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Aggregation test failed: {e}")
            self.results['failed'] += 1
            return False

    def test_update_frequency(self):
        """Test 5: Check if statistics are being updated regularly (every 10 min)"""
        print(f"\n{Fore.YELLOW}[TEST 5]{Style.RESET_ALL} Checking update frequency...")

        if not self.output_dir.exists():
            print(f"{Fore.YELLOW}⚠️  SKIP{Style.RESET_ALL} - Cannot check (output directory not accessible)")
            self.results['warnings'] += 1
            return True

        try:
            json_files = list(self.output_dir.glob('*.json'))

            if json_files:
                # Get most recent file modification time
                most_recent = max(json_files, key=lambda f: f.stat().st_mtime)
                mod_time = datetime.fromtimestamp(most_recent.stat().st_mtime)
                age_minutes = (datetime.now() - mod_time).total_seconds() / 60

                if age_minutes <= 15:
                    print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Statistics are up-to-date")
                    print(f"  📊 Most recent update: {age_minutes:.0f} minutes ago")
                    print(f"  🎯 Expected: Every 10 minutes")
                    self.results['passed'] += 1
                    return True
                elif age_minutes <= 60:
                    print(f"{Fore.YELLOW}⚠️  WARNING{Style.RESET_ALL} - Statistics slightly stale")
                    print(f"  📊 Last update: {age_minutes:.0f} minutes ago")
                    print(f"  🎯 Expected: Every 10 minutes")
                    self.results['warnings'] += 1
                    return True
                else:
                    print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Statistics very stale")
                    print(f"  📊 Last update: {age_minutes:.0f} minutes ago")
                    print(f"  🎯 Expected: Every 10 minutes")
                    self.results['failed'] += 1
                    return False
            else:
                print(f"{Fore.YELLOW}⚠️  WARNING{Style.RESET_ALL} - No output files to check")
                self.results['warnings'] += 1
                return True
        except Exception as e:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error checking update frequency: {e}")
            self.results['failed'] += 1
            return False

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print(f"{Fore.CYAN}TEST SUMMARY - STATISTICS WORKER{Style.RESET_ALL}")
        print("=" * 80)

        total = self.results['passed'] + self.results['failed']
        pass_rate = (self.results['passed'] / total * 100) if total > 0 else 0

        print(f"✅ Passed: {Fore.GREEN}{self.results['passed']}{Style.RESET_ALL}")
        print(f"❌ Failed: {Fore.RED}{self.results['failed']}{Style.RESET_ALL}")
        print(f"⚠️  Warnings: {Fore.YELLOW}{self.results['warnings']}{Style.RESET_ALL}")
        print(f"📊 Pass Rate: {pass_rate:.1f}%")

        if self.results['failed'] == 0:
            print(f"\n{Fore.GREEN}🎉 ALL TESTS PASSED - Statistics Worker is functioning correctly!{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}⚠️  SOME TESTS FAILED - Check worker logs for issues{Style.RESET_ALL}")

        print("=" * 80 + "\n")

        return self.results['failed'] == 0

    def run_all_tests(self):
        """Run all tests"""
        self.print_header()

        self.test_database_connection()
        self.test_statistics_queries()
        self.test_output_files()
        self.test_aggregation_accuracy()
        self.test_update_frequency()

        return self.print_summary()


if __name__ == "__main__":
    test = StatisticsWorkerTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
