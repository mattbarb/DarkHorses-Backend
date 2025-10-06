#!/usr/bin/env python3
"""
Clear all Racing API tables in Supabase
Uses PostgreSQL direct connection for fast truncation
"""

import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env.local'
load_dotenv(env_path)

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env.local")
    sys.exit(1)

# Tables to clear (in reverse dependency order)
TABLES = [
    'ra_results',
    'ra_runners',
    'ra_races',
    'ra_horse_pedigree',
    'ra_horses',
    'ra_owners',
    'ra_trainers',
    'ra_jockeys',
    'ra_bookmakers',
    'ra_courses',
]


def clear_tables():
    """Clear all racing API tables"""
    print("=" * 80)
    print("CLEARING SUPABASE RACING API TABLES")
    print("=" * 80)
    print(f"\nConnecting to database...")

    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        print(f"✓ Connected successfully\n")

        # Get row counts before clearing
        print("Current table counts:")
        print("-" * 80)
        for table in TABLES:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table:<25} {count:>10,} rows")
            except Exception as e:
                print(f"  {table:<25} ERROR: {e}")

        # Confirm deletion
        print("\n" + "=" * 80)
        response = input("Are you sure you want to TRUNCATE all these tables? (yes/no): ")

        if response.lower() != 'yes':
            print("\nOperation cancelled.")
            cursor.close()
            conn.close()
            return

        print("\n" + "=" * 80)
        print("TRUNCATING TABLES...")
        print("=" * 80 + "\n")

        # Clear tables
        for table in TABLES:
            try:
                # Use TRUNCATE for fast deletion with CASCADE to handle foreign keys
                cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                print(f"✓ Cleared {table}")
            except Exception as e:
                print(f"✗ Error clearing {table}: {e}")

        # Commit changes
        conn.commit()

        print("\n" + "=" * 80)
        print("Verifying tables are empty:")
        print("-" * 80)

        # Verify tables are empty
        all_empty = True
        for table in TABLES:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                status = "✓" if count == 0 else "✗"
                print(f"{status} {table:<25} {count:>10,} rows")
                if count > 0:
                    all_empty = False
            except Exception as e:
                print(f"✗ {table:<25} ERROR: {e}")
                all_empty = False

        print("=" * 80)

        if all_empty:
            print("\n✓ SUCCESS: All tables cleared successfully!")
        else:
            print("\n✗ WARNING: Some tables still contain data")

        # Close connection
        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    clear_tables()
