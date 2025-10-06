#!/usr/bin/env python3
"""
Test script for odds statistics tracker
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    try:
        from config import Config
        print("✅ Config imported")

        from database import DatabaseConnection
        print("✅ Database imported")

        from collectors import HistoricalOddsCollector, LiveOddsCollector
        print("✅ Collectors imported")

        from formatters import ConsoleFormatter, JSONFormatter
        print("✅ Formatters imported")

        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration"""
    print("\nTesting configuration...")
    try:
        from config import Config
        Config.validate()
        print(f"✅ Config validated")
        print(f"   Database: {Config.DATABASE_URL[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False

def test_database():
    """Test database connection"""
    print("\nTesting database connection...")
    try:
        from config import Config
        from database import DatabaseConnection

        db = DatabaseConnection(Config.DATABASE_URL)
        if db.test_connection():
            print("✅ Database connection successful")
            db.disconnect()
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("  ODDS STATISTICS TRACKER - TEST SUITE")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Database", test_database()))

    print("\n" + "=" * 60)
    print("  TEST RESULTS")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✅ All tests passed! Ready to use.")
        print("\nRun the tracker:")
        print("  python3 stats_tracker.py")
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
