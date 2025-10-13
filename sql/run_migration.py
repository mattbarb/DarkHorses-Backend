#!/usr/bin/env python3
"""
Quick script to check and run the race_name migration
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load env
env_file = Path(__file__).parent.parent / '.env MASTER.local'
if env_file.exists():
    load_dotenv(env_file)

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

if not supabase_url or not supabase_key:
    print('❌ SUPABASE_URL and SUPABASE_SERVICE_KEY required')
    sys.exit(1)

print(f'🔌 Connecting to Supabase...')
client = create_client(supabase_url, supabase_key)
print(f'✅ Connected')

# Check if race_name column exists
print('\n🔍 Checking if race_name column exists...')
try:
    response = client.table('ra_odds_historical').select('racing_bet_data_id, race_name').limit(1).execute()
    print('✅ race_name column ALREADY EXISTS!')
    print(f'   Sample: {response.data[0] if response.data else "No records yet"}')
    print('\n✅ Migration not needed - column already exists')
    sys.exit(0)
except Exception as e:
    if 'race_name' in str(e) and ('does not exist' in str(e) or 'column' in str(e).lower()):
        print('❌ race_name column does NOT exist')
        print('\n⚠️  Migration required but must be run in Supabase SQL Editor')
        print('   Supabase Python client cannot execute DDL statements')
        print('\n📋 Manual steps:')
        print('   1. Open Supabase SQL Editor: https://supabase.com/dashboard/project/amsjvmlaknnvppxsgpfk/sql')
        print('   2. Copy/paste contents of: sql/add_race_name_to_historical.sql')
        print('   3. Click "Run"')
        print('\n   Or use PostgreSQL directly with DATABASE_URL')
        sys.exit(1)
    else:
        print(f'❌ Unexpected error: {e}')
        sys.exit(1)
