#!/usr/bin/env python3
"""
Run All Worker Tests
Comprehensive test suite for all background workers
"""

import sys
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style, init

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))

from test_live_odds_worker import LiveOddsWorkerTest
from test_historical_odds_worker import HistoricalOddsWorkerTest
from test_statistics_worker import StatisticsWorkerTest

# Initialize colorama
init(autoreset=True)


def print_main_header():
    """Print main test suite header"""
    print("\n" + "=" * 80)
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'DarkHorses Backend Workers - Integration Test Suite':^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print("=" * 80)
    print(f"Testing all background workers: Live Odds, Historical Odds, Statistics")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")


def print_final_summary(results):
    """Print final summary of all tests"""
    print("\n" + "=" * 80)
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'FINAL TEST SUMMARY':^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print("=" * 80 + "\n")

    total_passed = sum(r['passed'] for r in results.values())
    total_failed = sum(r['failed'] for r in results.values())
    total_warnings = sum(r['warnings'] for r in results.values())
    total_tests = total_passed + total_failed

    # Print individual worker results
    print(f"{'Worker':<30} {'Passed':<10} {'Failed':<10} {'Warnings':<10} {'Status'}")
    print("-" * 80)

    for worker_name, result in results.items():
        passed = result['passed']
        failed = result['failed']
        warnings = result['warnings']

        if failed == 0:
            status = f"{Fore.GREEN}✅ PASS{Style.RESET_ALL}"
        else:
            status = f"{Fore.RED}❌ FAIL{Style.RESET_ALL}"

        print(f"{worker_name:<30} {passed:<10} {failed:<10} {warnings:<10} {status}")

    print("-" * 80)
    print(f"{'TOTAL':<30} {total_passed:<10} {total_failed:<10} {total_warnings:<10}")
    print()

    # Overall pass rate
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

    print(f"📊 Overall Pass Rate: {pass_rate:.1f}% ({total_passed}/{total_tests} tests)")
    print(f"⚠️  Total Warnings: {total_warnings}")
    print()

    # Final verdict
    if total_failed == 0:
        print(f"{Fore.GREEN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}🎉 ALL WORKERS FUNCTIONING CORRECTLY!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'=' * 80}{Style.RESET_ALL}")
        print()
        print(f"{Fore.GREEN}✅ Live Odds Worker: Collecting real-time odds{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ Historical Odds Worker: Backfilling historical data{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ Statistics Worker: Generating analytics{Style.RESET_ALL}")
        print()
    else:
        print(f"{Fore.RED}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.RED}⚠️  SOME WORKERS HAVE ISSUES{Style.RESET_ALL}")
        print(f"{Fore.RED}{'=' * 80}{Style.RESET_ALL}")
        print()
        print(f"🔍 Check individual test outputs above for details")
        print(f"📋 Review worker logs on Render.com for error messages")
        print()

    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")


def run_all_tests():
    """Run all worker tests"""
    print_main_header()

    results = {}

    # Test 1: Live Odds Worker
    try:
        print(f"\n{Fore.YELLOW}{'▶' * 40}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Running Live Odds Worker Tests...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'▶' * 40}{Style.RESET_ALL}\n")

        live_test = LiveOddsWorkerTest()
        live_test.run_all_tests()
        results['Live Odds Worker'] = live_test.results
    except Exception as e:
        print(f"{Fore.RED}❌ Live Odds Worker tests crashed: {e}{Style.RESET_ALL}")
        results['Live Odds Worker'] = {'passed': 0, 'failed': 1, 'warnings': 0}

    # Test 2: Historical Odds Worker
    try:
        print(f"\n{Fore.YELLOW}{'▶' * 40}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Running Historical Odds Worker Tests...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'▶' * 40}{Style.RESET_ALL}\n")

        historical_test = HistoricalOddsWorkerTest()
        historical_test.run_all_tests()
        results['Historical Odds Worker'] = historical_test.results
    except Exception as e:
        print(f"{Fore.RED}❌ Historical Odds Worker tests crashed: {e}{Style.RESET_ALL}")
        results['Historical Odds Worker'] = {'passed': 0, 'failed': 1, 'warnings': 0}

    # Test 3: Statistics Worker
    try:
        print(f"\n{Fore.YELLOW}{'▶' * 40}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Running Statistics Worker Tests...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'▶' * 40}{Style.RESET_ALL}\n")

        stats_test = StatisticsWorkerTest()
        stats_test.run_all_tests()
        results['Statistics Worker'] = stats_test.results
    except Exception as e:
        print(f"{Fore.RED}❌ Statistics Worker tests crashed: {e}{Style.RESET_ALL}")
        results['Statistics Worker'] = {'passed': 0, 'failed': 1, 'warnings': 0}

    # Print final summary
    print_final_summary(results)

    # Return exit code
    total_failed = sum(r['failed'] for r in results.values())
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
