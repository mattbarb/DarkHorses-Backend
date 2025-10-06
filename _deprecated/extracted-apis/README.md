# APIs Extracted to Separate Repository

⚠️ **Note**: The API code in this folder has been extracted and moved to a separate repository.

## New Repository

**DarkHorses-Backend-API**
- **GitHub**: https://github.com/mattbarb/DarkHorses-Backend-API
- **Local**: `/Users/matthewbarber/Documents/GitHub/DarkHorses-Backend-API`

## What Was Moved

The APIs in this `extracted-apis/` folder were combined into a single unified API:

### Before (2 separate APIs)
```
extracted-apis/
├── odds-api/         # DarkHorses odds endpoints
└── masters-api/      # Racing reference data
```

### After (1 unified API)
```
DarkHorses-Backend-API/
└── main.py           # Combined API with /api/odds/* and /api/masters/*
```

## Benefits of Consolidation

- ✅ Single deployment instead of two
- ✅ Shared middleware and configuration
- ✅ Unified documentation at `/docs`
- ✅ Lower cost ($7/month instead of $14)

## Architecture

This repository (**DarkHorses-Backend-Workers**) contains ONLY the background workers:
- Live Odds Worker
- Historical Odds Worker
- Statistics Worker

The API is now deployed separately from: **DarkHorses-Backend-API**

## For Development

To work on the API, use the new repository:
```bash
cd /Users/matthewbarber/Documents/GitHub/DarkHorses-Backend-API
```

This folder is kept for reference only.
