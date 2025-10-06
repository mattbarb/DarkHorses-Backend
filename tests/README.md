# Worker Integration Tests

Comprehensive test suite to verify all background workers are functioning correctly by querying Supabase tables and checking data integrity.

## Overview

This test suite validates:
- ✅ **Live Odds Worker** - Real-time odds collection from Racing API
- ✅ **Historical Odds Worker** - Historical data backfill and race results
- ✅ **Statistics Worker** - Aggregation and analytics generation

## Quick Start

### Run All Tests

```bash
cd tests
python3 run_all_tests.py
```

### Run Individual Worker Tests

```bash
# Test live odds worker only
python3 test_live_odds_worker.py

# Test historical odds worker only
python3 test_historical_odds_worker.py

# Test statistics worker only
python3 test_statistics_worker.py
```

## Requirements

```bash
pip install supabase colorama psycopg2-binary python-dotenv
```

**Note**: These dependencies are already in the root `requirements.txt`.

## Environment Variables

Tests require the following environment variables (from `.env.local` or `.env`):

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key
DATABASE_URL=postgresql://postgres:password@db.supabase.co:5432/postgres
```

## Test Details

### Live Odds Worker Tests

**File**: `test_live_odds_worker.py`

**Tests**:
1. ✅ Table exists with data
2. ✅ Recent updates (within 30 minutes)
3. ✅ Data coverage (races, horses, bookmakers)
4. ✅ Data quality (no nulls in critical fields)
5. ✅ Adaptive scheduling (multiple updates per race)

**Expected Output**:
```
🏇 LIVE ODDS WORKER TEST
================================================================================
[TEST 1] Checking if ra_odds_live table exists...
✅ PASS - Table exists with 2,645 total records

[TEST 2] Checking for recent updates...
✅ PASS - Found 2,645 records updated in last 30 minutes
  Sample: Amber Honey @ Wolverhampton
          BetVictor - Odds: 4.5
          Updated: 2025-10-06T14:30:10

[TEST 3] Checking data coverage...
✅ PASS - Data coverage for today:
  🏁 Unique races: 15
  🐴 Unique horses: 120
  📊 Unique bookmakers: 26

[TEST 4] Checking data quality...
✅ PASS - All critical fields populated in 100 sample records

[TEST 5] Checking adaptive scheduling...
✅ PASS - Adaptive scheduling detected
  Found 8 races with multiple updates
  Max update timestamps for single race: 5

TEST SUMMARY - LIVE ODDS WORKER
================================================================================
✅ Passed: 5
❌ Failed: 0
⚠️  Warnings: 0
📊 Pass Rate: 100.0%

🎉 ALL TESTS PASSED - Live Odds Worker is functioning correctly!
```

### Historical Odds Worker Tests

**File**: `test_historical_odds_worker.py`

**Tests**:
1. ✅ Table exists with data
2. ✅ Date coverage (2015 to present)
3. ✅ Recent backfill activity (last 7 days)
4. ✅ Race results present (finishing positions)
5. ✅ Data quality (no nulls in critical fields)
6. ✅ Backfill progress toward 2015 goal

**Key Metrics**:
- Date range coverage
- Unique dates backfilled
- Finishing position completeness
- Progress toward 2015 target

### Statistics Worker Tests

**File**: `test_statistics_worker.py`

**Tests**:
1. ✅ Database connection for queries
2. ✅ Statistics queries execute successfully
3. ✅ Output JSON files exist and are recent
4. ✅ Aggregation accuracy
5. ✅ Update frequency (every 10 minutes)

**Validates**:
- Direct PostgreSQL connection
- COUNT DISTINCT aggregations
- JSON file freshness
- Data consistency

## Interpreting Results

### Test Status Indicators

- 🟢 **✅ PASS** - Test passed successfully
- 🔴 **❌ FAIL** - Test failed, worker may have issues
- 🟡 **⚠️  WARNING** - Test passed but with caveats

### Common Warnings

**Live Odds**:
- ⚠️  Low bookmaker count - Racing API may be down or limited bookmakers available
- ⚠️  No multiple updates - Only one fetch cycle has run, normal for recent deployment

**Historical Odds**:
- ⚠️  Latest date not recent - Daily backfill runs at 1:00 AM UK time
- ⚠️  No finishing positions - Data may be for upcoming races
- ⚠️  Backfill in progress - Expected until backfill reaches 2015

**Statistics**:
- ⚠️  Output directory not accessible - Tests running remotely, files only on Render
- ⚠️  Slightly stale - Last update was 15-60 minutes ago, still acceptable

### Common Failures

**All Workers**:
- ❌ Missing environment variables - Check `.env.local` exists
- ❌ Database connection failed - Check DATABASE_URL is correct

**Live Odds**:
- ❌ No recent updates - Worker may have crashed or not running
- ❌ No data for today - Worker hasn't successfully fetched yet

**Historical Odds**:
- ❌ Table empty - Backfill hasn't started (runs immediately on first deploy)

## CI/CD Integration

### Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

### GitHub Actions Example

```yaml
name: Worker Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python3 tests/run_all_tests.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

## Troubleshooting

### Tests Can't Connect to Database

```bash
# Verify environment variables are loaded
python3 -c "import os; from dotenv import load_dotenv; load_dotenv('.env.local'); print(os.getenv('SUPABASE_URL'))"
```

### Tests Show Stale Data

Workers update on different schedules:
- **Live Odds**: Every 10s - 15min (adaptive based on race proximity)
- **Historical Odds**: Daily at 1:00 AM UK time
- **Statistics**: Every 10 minutes

Wait for next scheduled run or check Render logs for errors.

### All Tests Fail

1. Check workers are running on Render.com
2. Verify environment variables are set correctly
3. Check Render deployment logs for startup errors
4. Ensure Starter plan (not free tier) to keep workers always-on

## Development

### Adding New Tests

```python
def test_new_feature(self):
    """Test N: Description of what this tests"""
    print(f"\n{Fore.YELLOW}[TEST N]{Style.RESET_ALL} Checking new feature...")

    try:
        # Your test logic here
        response = self.client.table('table_name').select('*').execute()

        if response.data:
            print(f"{Fore.GREEN}✅ PASS{Style.RESET_ALL} - Test passed")
            self.results['passed'] += 1
            return True
        else:
            print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Test failed")
            self.results['failed'] += 1
            return False
    except Exception as e:
        print(f"{Fore.RED}❌ FAIL{Style.RESET_ALL} - Error: {e}")
        self.results['failed'] += 1
        return False
```

Add the new test method call to `run_all_tests()`.

### Test Best Practices

1. **Be defensive** - Handle missing data gracefully (warnings, not failures)
2. **Provide context** - Print sample data to help debug issues
3. **Time-aware** - Account for scheduled run times (1 AM daily, every 10 min, etc.)
4. **Clear output** - Use colors and emojis for quick visual scanning

## Output Examples

### All Tests Passing

```
================================================================================
                 DarkHorses Backend Workers - Integration Test Suite
================================================================================

Worker                         Passed     Failed     Warnings   Status
--------------------------------------------------------------------------------
Live Odds Worker               5          0          0          ✅ PASS
Historical Odds Worker         6          0          1          ✅ PASS
Statistics Worker              5          0          2          ✅ PASS
--------------------------------------------------------------------------------
TOTAL                          16         0          3

📊 Overall Pass Rate: 100.0% (16/16 tests)
⚠️  Total Warnings: 3

================================================================================
🎉 ALL WORKERS FUNCTIONING CORRECTLY!
================================================================================

✅ Live Odds Worker: Collecting real-time odds
✅ Historical Odds Worker: Backfilling historical data
✅ Statistics Worker: Generating analytics
```

### Some Tests Failing

```
================================================================================
                 DarkHorses Backend Workers - Integration Test Suite
================================================================================

Worker                         Passed     Failed     Warnings   Status
--------------------------------------------------------------------------------
Live Odds Worker               3          2          0          ❌ FAIL
Historical Odds Worker         5          1          1          ❌ FAIL
Statistics Worker              5          0          2          ✅ PASS
--------------------------------------------------------------------------------
TOTAL                          13         3          3

📊 Overall Pass Rate: 81.3% (13/16 tests)
⚠️  Total Warnings: 3

================================================================================
⚠️  SOME WORKERS HAVE ISSUES
================================================================================

🔍 Check individual test outputs above for details
📋 Review worker logs on Render.com for error messages
```

## Additional Resources

- **Render Deployment**: https://render.com/docs
- **Supabase Docs**: https://supabase.com/docs
- **Racing API**: Check CLAUDE.md for endpoint documentation
- **Worker Architecture**: See MICROSERVICES_ARCHITECTURE.md

## License

Part of the DarkHorses-Backend-Workers project.
