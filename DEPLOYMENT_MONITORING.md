# Change Detection Deployment - Monitoring Guide

## Deployment Status

**Pushed to GitHub**: ✅ Committed and pushed to `main` branch
**Auto-Deploy**: ⏳ Render.com will auto-deploy in ~2-5 minutes
**Service**: `darkhorses-workers` (Odds Workers Service)

---

## What to Monitor

### 1. Render.com Deployment

**URL**: https://dashboard.render.com/

**Service**: `darkhorses-workers`

**Steps**:
1. Go to Render.com dashboard
2. Select `darkhorses-workers` service
3. Click "Logs" tab
4. Watch for deployment messages:
   ```
   ==> Building...
   ==> Deploying...
   ==> Service started
   ```

**Expected deployment time**: 2-5 minutes

---

### 2. Log Patterns to Watch For

#### ✅ SUCCESS INDICATORS

**First Fetch Cycle** (should see within 30 seconds of deployment):
```
🚀 STARTING LIVE ODDS SCHEDULER
🎯 RUNNING IMMEDIATE INITIAL FETCH...

📊 STAGE 2: INSERTING TO SUPABASE (WITH CHANGE DETECTION)
🔍 Change detection: comparing against 3 races in database...
📭 No existing odds found (all records are new)
📊 Change detection: 2584 to update/insert, 0 unchanged (skipped)

✅ STAGE 2 COMPLETE - DATABASE UPDATE WITH CHANGE DETECTION
   Records inserted: 2584 (new)
   Records updated: 0 (odds changed)
   Records skipped: 0 (odds unchanged)
   💰 Database cost savings: 0 unnecessary writes avoided

✅ Cycle complete: 2584 updated | 0 skipped | 3 races | 33 horses | 26 bookmakers | 0 errors
```

**Second Fetch Cycle** (after 60-900 seconds):
```
📊 STAGE 2: INSERTING TO SUPABASE (WITH CHANGE DETECTION)
🔍 Change detection: comparing against 3 races in database...
✅ Loaded 2584 existing odds records for comparison
📊 Change detection: 127 to update/insert, 2457 unchanged (skipped)

✅ STAGE 2 COMPLETE - DATABASE UPDATE WITH CHANGE DETECTION
   Records inserted: 0 (new)
   Records updated: 127 (odds changed)
   Records skipped: 2457 (odds unchanged)
   💰 Database cost savings: 2457 unnecessary writes avoided

✅ Cycle complete: 127 updated | 2457 skipped | 3 races | 33 horses | 26 bookmakers | 0 errors
```

**Stable Odds Period** (ideal scenario):
```
📊 STAGE 2: INSERTING TO SUPABASE (WITH CHANGE DETECTION)
🔍 Change detection: comparing against 3 races in database...
✅ Loaded 2584 existing odds records for comparison
📊 Change detection: 0 to update/insert, 2584 unchanged (skipped)

✅ No odds changes detected - skipping database write (reduces cost)

✅ Cycle complete: 0 updated | 2584 skipped | 3 races | 33 horses | 26 bookmakers | 0 errors
```

---

#### ❌ FAILURE INDICATORS

**Change detection not working**:
```
❌ Error fetching existing odds: <error message>
```
**Action**: Check Supabase credentials and network connectivity
**Impact**: Falls back to upserting all (works but no optimization)

**Always skipped: 0**:
```
✅ Cycle complete: 2584 updated | 0 skipped | ...
✅ Cycle complete: 2584 updated | 0 skipped | ...
✅ Cycle complete: 2584 updated | 0 skipped | ...
```
**Action**: Change detection not activating - investigate why
**Impact**: No optimization, same as before

**Database errors**:
```
❌ Upsert error to ra_odds_live: <error>
```
**Action**: Check Supabase connection and table schema
**Impact**: Data not being stored

---

### 3. Performance Metrics

#### Key Statistics to Track

**Metric 1: Skip Rate**
```
Skip Rate = skipped / (inserted + updated + skipped) × 100%

Target: 80-95% during stable odds periods
```

**Example calculation**:
- Cycle 1: 2584 inserted, 0 updated, 0 skipped → 0% skip rate (expected first cycle)
- Cycle 2: 0 inserted, 127 updated, 2457 skipped → 95% skip rate ✅
- Cycle 3: 0 inserted, 0 updated, 2584 skipped → 100% skip rate ✅

**Metric 2: Database Write Reduction**
```
Before: ~2,500 writes per cycle
After (stable): ~0-500 writes per cycle
Reduction: 80-100%
```

**Metric 3: Cycle Duration**
```
Before: ~2,500ms per cycle
After: ~650-1,150ms per cycle (includes 100ms existing odds fetch)
```

---

### 4. Database Health Check

**Supabase Dashboard**: https://supabase.com/dashboard/project/amsjvmlaknvnppxsgpfk

**Check**:
1. **Table Statistics** (`ra_odds_live`):
   - Row count should be ~2,500-3,000 (current races)
   - Not growing unbounded (old races cleaned up)

2. **Query Performance**:
   - Go to "Database" → "Query" → "Performance"
   - Look for slow queries (>1 second)
   - Verify `fetch_existing_odds_for_races` is fast (<200ms)

3. **Database Activity**:
   - Go to "Database" → "Activity"
   - Should see MUCH fewer INSERT/UPDATE operations
   - Mostly SELECT operations (change detection queries)

---

### 5. Cost Analysis

**Before Optimization** (estimated):
```
Writes per hour: 60 cycles × 2,500 writes = 150,000 writes
Writes per day: 150,000 × 24 = 3,600,000 writes
Writes per month: 3.6M × 30 = 108,000,000 writes
```

**After Optimization** (estimated, 50% stable odds):
```
Stable periods (50% of time): 60 cycles × 100 writes = 6,000/hour
Volatile periods (50% of time): 60 cycles × 1,000 writes = 60,000/hour
Average: 33,000 writes/hour
Writes per day: 33,000 × 24 = 792,000 writes
Writes per month: 792,000 × 30 = 23,760,000 writes

Reduction: 78% fewer writes
```

**Check Supabase billing**:
- Go to "Settings" → "Billing"
- Monitor "Database egress" and "Storage writes"
- Should see significant decrease after 24 hours

---

## Timeline

### T+0 (Push to GitHub) ✅
- Code committed
- GitHub Actions triggered (if configured)
- Render.com webhook received

### T+2 min (Build Start)
- Render.com starts build
- Installs dependencies
- Creates new service image

### T+5 min (Deployment)
- New code deployed
- Service restarted
- First fetch cycle runs immediately

### T+6 min (First Stats)
- First cycle complete (all inserts)
- Logs show change detection messages

### T+10 min (Second Stats)
- Second cycle complete
- Should see `skipped > 0` if odds stable

### T+30 min (Stable Pattern)
- Clear pattern emerges:
  - Some cycles: high skip rate
  - Other cycles: partial updates
  - Occasional cycles: all skipped

### T+24 hours (Full Analysis)
- Calculate average skip rate
- Measure database write reduction
- Verify cost savings in Supabase billing

---

## Quick Health Check Commands

### Check Recent Logs (Last 100 lines)
```bash
# Via Render.com CLI
render logs --service darkhorses-workers --tail 100
```

### Search for Change Detection Messages
```bash
# Via Render.com dashboard
# Logs tab → Filter: "change detection"
# Should see regular messages every 60-900 seconds
```

### Count Skip vs Update Cycles
```bash
# Via Render.com dashboard
# Logs tab → Filter: "skipped"
# Count occurrences of:
#   "skipped: 0" (no optimization) vs
#   "skipped: 2000+" (optimization working)
```

---

## Rollback Plan (If Issues Occur)

### Immediate Rollback
```bash
# Via Render.com dashboard:
# 1. Go to darkhorses-workers service
# 2. Click "Manual Deploy" dropdown
# 3. Select previous commit: 3b3e676
# 4. Click "Deploy"
# Service will roll back to previous version
```

### Git Rollback
```bash
# If needed, revert the commit:
git revert d6c0a67
git push origin main
# Render.com will auto-deploy the revert
```

**When to rollback**:
- ❌ Continuous database errors
- ❌ Service crashes
- ❌ No data being stored
- ❌ Performance degradation (cycles taking >5 seconds)

**When NOT to rollback**:
- ⚠️ Change detection shows "Error fetching existing odds" but data still writes
  - This is fallback behavior (safe, just no optimization)
- ⚠️ Skip rate lower than expected (e.g., 40% instead of 80%)
  - This might be volatile market conditions (not a bug)

---

## Expected Results Summary

### ✅ Optimal Scenario
```
📊 Hour 1 Analysis:
   - 60 fetch cycles
   - 45 cycles: skipped > 80% (stable odds)
   - 10 cycles: skipped 40-80% (partial changes)
   - 5 cycles: skipped < 40% (volatile odds)
   - Average skip rate: 75%
   - Database writes: 37,500 (down from 150,000)
   - Cost savings: 75%
```

### ⚠️ Acceptable Scenario
```
📊 Hour 1 Analysis (volatile market):
   - 60 fetch cycles
   - 20 cycles: skipped > 50%
   - 30 cycles: skipped 20-50%
   - 10 cycles: skipped < 20%
   - Average skip rate: 40%
   - Database writes: 90,000 (down from 150,000)
   - Cost savings: 40%
```

### ❌ Problem Scenario
```
📊 Hour 1 Analysis (not working):
   - 60 fetch cycles
   - 0 cycles: skipped > 0
   - All cycles: "0 skipped"
   - No change detection messages
   - Database writes: 150,000 (same as before)
   - Cost savings: 0%
   - ACTION REQUIRED: Investigate logs
```

---

## Monitoring Checklist

### First 10 Minutes ✅
- [ ] Deployment completed successfully
- [ ] Service restarted without errors
- [ ] First fetch cycle shows "change detection" messages
- [ ] Logs show "Loaded X existing odds records"
- [ ] No continuous error messages

### First Hour ✅
- [ ] Multiple cycles completed
- [ ] At least one cycle shows `skipped > 0`
- [ ] Log pattern alternates between updates and skips
- [ ] No database connection errors
- [ ] Service uptime: 100%

### First Day ✅
- [ ] Skip rate averaging 60-95%
- [ ] Database writes reduced by 60-95%
- [ ] No performance degradation
- [ ] Supabase dashboard shows reduced activity
- [ ] All races have current odds data

---

## Support Contacts

**Supabase Support**: https://supabase.com/support
**Render.com Support**: https://render.com/support
**Project Repository**: https://github.com/mattbarb/DarkHorses-Odds-Workers

**Deployment Documentation**:
- `/CHANGE_DETECTION_IMPLEMENTATION.md` - Full technical details
- `/CLAUDE.md` - System architecture
- `/render.yaml` - Deployment configuration

---

**Deployment Date**: October 9, 2025
**Expected Completion**: T+5 minutes from push
**Monitoring Period**: 24 hours
**Status**: 🟢 DEPLOYED - Monitor logs for confirmation
