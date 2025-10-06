# 🔧 How to Get the Correct Session Pooler URL from Supabase

## Current Problem

Your `.env.local` file has:

```bash
# ❌ IPv6-only (won't work on Render)
DATABASE_URL=postgresql://postgres:ujCx2aXH!RYnU6x@db.amsjvmlaknnvppxsgpfk.supabase.co:5432/postgres

# ❌ Still IPv6-only (same host, different port)
TRANSACTION_POOLER=postgresql://postgres:ujCx2aXH!RYnU6x@db.amsjvmlaknnvppxsgpfk.supabase.co:6543/postgres
```

**Both URLs use `db.amsjvmlaknnvppxsgpfk.supabase.co`** which is **IPv6-only** and won't work on Render.com.

---

## What You Need

You need the **Session Pooler** URL which looks like:

```bash
# ✅ IPv4 compatible (will work on Render)
SESSION_POOLER=postgresql://postgres:ujCx2aXH!RYnU6x@aws-0-us-west-1.pooler.supabase.com:5432/postgres
```

Notice the hostname is different: `aws-0-us-west-1.pooler.supabase.com` instead of `db.*.supabase.co`

---

## Step-by-Step Instructions

### 1. Go to Supabase Dashboard
Visit: https://supabase.com/dashboard/project/amsjvmlaknnvppxsgpfk

### 2. Navigate to Database Settings
- Click **Settings** (gear icon in left sidebar)
- Click **Database**

### 3. Find Connection Pooling Section
Scroll down to the section titled **"Connection Pooling"**

### 4. Select Session Mode
You should see tabs for different pooling modes:
- **Session** ← Use this one
- Transaction
- Statement

Click on **Session** mode.

### 5. Copy the Connection String
You'll see a connection string that looks like:

```
postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-us-west-1.pooler.supabase.com:5432/postgres
```

**Important notes:**
- The hostname will be `aws-0-us-west-1.pooler.supabase.com` (or similar region)
- The port will be **5432** (Session mode uses 5432, not 6543)
- The password is the same as your database password

### 6. Update Your .env Files

**Local (.env.local):**
```bash
# Add this line:
SESSION_POOLER=postgresql://postgres:ujCx2aXH!RYnU6x@aws-0-us-west-1.pooler.supabase.com:5432/postgres
```

**Render.com:**
- Go to your Render.com dashboard
- Select your DarkHorses Odds API service
- Click **Environment** tab
- Add/Update environment variable:
  - Key: `SESSION_POOLER`
  - Value: `postgresql://postgres:ujCx2aXH!RYnU6x@aws-0-us-west-1.pooler.supabase.com:5432/postgres`
- Click **Save Changes**
- Render will automatically redeploy

---

## Alternative: Use Transaction Pooler with Correct URL

If you prefer transaction pooling, get the Transaction Pooler URL from Supabase:

**Transaction mode:**
```bash
TRANSACTION_POOLER=postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

The key is that it must use `pooler.supabase.com` hostname, NOT `db.*.supabase.co`.

---

## Why This Fixes Statistics

Once you add the correct `SESSION_POOLER` URL:

1. ✅ Statistics module will use it (we updated config.py to check SESSION_POOLER first)
2. ✅ DNS resolution will work (pooler.supabase.com has IPv4 A records)
3. ✅ Connection will succeed on Render (IPv4 compatible)
4. ✅ Statistics will calculate and save to JSON files
5. ✅ Dashboard will show statistics data

---

## Verify It Works

After adding SESSION_POOLER and deploying to Render:

```bash
# Test the statistics refresh endpoint
curl -X POST https://darkhorses-odds-api.onrender.com/api/statistics/refresh

# Should return success with stats data
```

Or check the dashboard at: https://darkhorses-odds-api.onrender.com/

---

## Summary

| Variable | Current Status | Action Needed |
|----------|---------------|---------------|
| `DATABASE_URL` | ❌ IPv6-only `db.*.supabase.co` | Keep as-is (used elsewhere) |
| `TRANSACTION_POOLER` | ❌ IPv6-only `db.*.supabase.co:6543` | Update to use `pooler.supabase.com:6543` OR keep as-is |
| `SESSION_POOLER` | ❌ Not set | **ADD THIS** - Get from Supabase → Database → Connection Pooling → Session mode |

**Required action:** Get Session Pooler URL from Supabase and add as `SESSION_POOLER` environment variable on Render.

---

## Quick Reference: Connection String Format

```
postgresql://[user]:[password]@[host]:[port]/[database]

✅ Correct host: aws-0-us-west-1.pooler.supabase.com
❌ Wrong host:   db.amsjvmlaknnvppxsgpfk.supabase.co

Session mode:      port 5432
Transaction mode:  port 6543
```

The critical part is the **hostname** - it must be `pooler.supabase.com`, not `db.*.supabase.co`.
