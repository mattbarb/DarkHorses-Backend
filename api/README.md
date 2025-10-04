# DarkHorses Racing Odds API

FastAPI server providing access to live odds, historical odds, statistics, and scheduler information.

## Installation

```bash
cd api
pip install -r requirements.txt
```

## Running the API

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- **Interactive docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative docs (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

## Endpoints

### Health Check
```
GET /
```
Returns API status and available endpoints.

### Live Odds

#### Get Live Odds
```
GET /api/live-odds?race_date=2025-10-04&course=Ascot&limit=100&offset=0
```

**Query Parameters:**
- `race_date` (optional): Filter by race date (YYYY-MM-DD)
- `course` (optional): Filter by course name (partial match)
- `bookmaker` (optional): Filter by bookmaker name (partial match)
- `limit` (optional): Number of records to return (1-1000, default: 100)
- `offset` (optional): Number of records to skip (default: 0)

**Response:**
```json
{
  "success": true,
  "count": 100,
  "limit": 100,
  "offset": 0,
  "data": [
    {
      "id": "...",
      "race_id": "...",
      "horse_id": "...",
      "bookmaker_name": "Bet365",
      "odds_decimal": 3.50,
      "odds_fractional": "5/2",
      "race_date": "2025-10-04",
      "race_time": "14:30:00",
      "course": "Ascot",
      "horse_name": "Thunder Strike",
      ...
    }
  ]
}
```

#### Get Upcoming Races
```
GET /api/live-odds/upcoming-races?hours_ahead=24
```

**Query Parameters:**
- `hours_ahead` (optional): Look ahead this many hours (1-168, default: 24)

**Response:**
```json
{
  "success": true,
  "count": 15,
  "data": [
    {
      "race_id": "...",
      "race_date": "2025-10-04",
      "race_time": "14:30:00",
      "course": "Ascot",
      "country": "GB",
      "race_name": "Queen Elizabeth Stakes"
    }
  ]
}
```

### Historical Odds

#### Get Historical Odds
```
GET /api/historical-odds?year=2024&course=Ascot&limit=100&offset=0
```

**Query Parameters:**
- `race_date` (optional): Filter by race date (YYYY-MM-DD)
- `course` (optional): Filter by course name (partial match)
- `year` (optional): Filter by year (2015-2025)
- `limit` (optional): Number of records to return (1-1000, default: 100)
- `offset` (optional): Number of records to skip (default: 0)

**Response:**
```json
{
  "success": true,
  "count": 100,
  "limit": 100,
  "offset": 0,
  "data": [
    {
      "id": "...",
      "race_id": "...",
      "horse_id": "...",
      "bookmaker_name": "Bet365",
      "odds_decimal": 3.50,
      "race_date": "2024-06-15",
      "finishing_position": 1,
      ...
    }
  ]
}
```

### Statistics

#### Get Statistics
```
GET /api/statistics?table=all
```

**Query Parameters:**
- `table` (optional): Which stats to return - `live`, `historical`, or `all` (default: `all`)

**Response:**
```json
{
  "success": true,
  "data": {
    "live": {
      "timestamp": "2025-10-04T12:00:00",
      "ra_odds_live": {
        "basic_metrics": {
          "total_records": 15000,
          "earliest_race_date": "2025-10-04",
          "latest_race_date": "2025-10-05"
        },
        "unique_entities": {
          "unique_races": 45,
          "unique_horses": 450,
          "unique_bookmakers": 26
        },
        ...
      }
    },
    "historical": {
      "timestamp": "2025-10-04T12:00:00",
      "rb_odds_historical": {
        ...
      }
    }
  }
}
```

### Scheduler Status

#### Get Scheduler Status
```
GET /api/scheduler-status
```

Returns detailed information about all schedulers, their timing, and configuration.

**Response:**
```json
{
  "success": true,
  "schedulers": {
    "live_odds": {
      "name": "Live Odds Fetcher",
      "schedule": "Every 5 minutes (adaptive)",
      "details": {
        "frequency": "5 minutes default",
        "adaptive_schedule": {
          "race_starting_soon": "Every 1 minute",
          "race_today": "Every 5 minutes",
          "race_tomorrow": "Every 30 minutes"
        },
        "coverage": "Today + Tomorrow (GB & IRE)",
        "stop_updating": "When race starts"
      }
    },
    "historical_odds": {
      "name": "Historical Odds Fetcher",
      "schedule": "Daily at 1:00 AM UK time",
      "details": {
        "daily_fetch": "1:00 AM UK time",
        "backfill_mode": "On-demand",
        "coverage": "GB & IRE races from 2015"
      }
    },
    "statistics_updater": {
      "name": "Statistics Tracker",
      "schedule": "Automatic after each fetch cycle",
      "details": {
        "trigger": "After successful fetch cycles",
        "output_location": "odds_statistics/output/"
      }
    }
  },
  "system_info": {
    "timezone": "UK Time (GMT/BST)",
    "database": "Supabase PostgreSQL",
    "api_source": "Racing API",
    "regions_covered": ["GB", "IRE"]
  }
}
```

### Reference Data

#### Get Bookmakers
```
GET /api/bookmakers
```

Returns list of all bookmakers in the system.

**Response:**
```json
{
  "success": true,
  "count": 26,
  "data": [
    {
      "id": "bet365",
      "name": "Bet365",
      "type": "fixed"
    }
  ]
}
```

#### Get Courses
```
GET /api/courses
```

Returns list of all courses/tracks in the system.

**Response:**
```json
{
  "success": true,
  "count": 60,
  "data": [
    {
      "name": "Ascot",
      "country": "GB"
    }
  ]
}
```

## CORS Configuration

The API is configured with permissive CORS settings for development. For production, update the `allow_origins` in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Environment Variables

Ensure these are set in your `.env` or `.env.local` file:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key_here
```

## Example Usage

### Using curl

```bash
# Get live odds for today
curl "http://localhost:8000/api/live-odds?race_date=2025-10-04"

# Get upcoming races
curl "http://localhost:8000/api/live-odds/upcoming-races"

# Get historical odds for 2024
curl "http://localhost:8000/api/historical-odds?year=2024&limit=50"

# Get statistics
curl "http://localhost:8000/api/statistics"

# Get scheduler status
curl "http://localhost:8000/api/scheduler-status"
```

### Using JavaScript/Fetch

```javascript
// Get live odds
const response = await fetch('http://localhost:8000/api/live-odds?race_date=2025-10-04');
const data = await response.json();
console.log(data);

// Get statistics
const statsResponse = await fetch('http://localhost:8000/api/statistics?table=all');
const stats = await statsResponse.json();
console.log(stats);
```

### Using Python

```python
import requests

# Get live odds
response = requests.get('http://localhost:8000/api/live-odds', params={
    'race_date': '2025-10-04',
    'limit': 100
})
data = response.json()
print(data)
```

## Deployment

### Using Docker

```bash
# Build image
docker build -t darkhorses-api .

# Run container
docker run -d -p 8000:8000 --env-file .env darkhorses-api
```

### Using systemd

Create `/etc/systemd/system/darkhorses-api.service`:

```ini
[Unit]
Description=DarkHorses Racing Odds API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/DarkHorses-Backend/api
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable darkhorses-api
sudo systemctl start darkhorses-api
```

## Production Considerations

1. **Rate Limiting**: Add rate limiting middleware to prevent abuse
2. **Authentication**: Add API key or JWT authentication for admin endpoints
3. **Caching**: Implement Redis caching for frequently accessed data
4. **Monitoring**: Add logging and monitoring (e.g., Sentry, DataDog)
5. **HTTPS**: Always use HTTPS in production with valid SSL certificates
6. **Database Connection Pooling**: Configure Supabase connection pooling

## Troubleshooting

### API won't start

Check environment variables:
```bash
echo $SUPABASE_URL
echo $SUPABASE_SERVICE_KEY
```

### Empty responses

Verify data exists in tables:
```bash
# Check live odds
curl "http://localhost:8000/api/live-odds?limit=1"

# Check statistics files exist
ls -la ../odds_statistics/output/
```

### CORS errors

Update CORS configuration in `main.py` to allow your frontend domain.
