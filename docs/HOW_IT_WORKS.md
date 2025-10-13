# DarkHorses-Odds-Workers - How It Works

> **Prerequisites:** Read [Idiot's Guide](IDIOTS_GUIDE.md) first for context

## Overview

This document walks through the code and explains how everything works together.

DarkHorses-Odds-Workers is built using Python, Web Scraping, Celery.

## The Big Picture

```mermaid
sequenceDiagram
    participant Trigger
    participant Main
    participant Service
    participant DB
    participant External

    Trigger->>Main: 1. Start
    Main->>Service: 2. Initialize
    Service->>External: 3. Fetch data
    External->>Service: 4. Return data
    Service->>DB: 5. Store
    DB->>Main: 6. Success
```

## Code Structure

```
DarkHorses-Odds-Workers/
├── main.py           # Entry point - starts everything
├── config.py         # Configuration loading
├── services/
│   ├── service1.py   # Core logic
│   └── service2.py   # Helper functions
├── models/
│   └── models.py     # Data models
├── utils/
│   └── helpers.py    # Utility functions
└── tests/
    └── test_*.py     # Unit tests
```

### Key Files

#### 1. `main.py` - The Starting Point

**What it does:**
- Loads configuration from environment variables
- Initializes database connections
- Sets up logging
- Starts the main service loop

**Code walkthrough:**
```python
# Line 1-10: Imports
import config
from services import MainService

# Line 15-20: Load config
config = load_config()

# Line 25-35: Initialize services
service = MainService(config)

# Line 40-50: Run
if __name__ == "__main__":
    service.run()
```

**When you run `python main.py`:**
1. Loads .env file
2. Connects to database
3. Starts main loop
4. Waits for work to do

#### 2. `services/main_service.py` - The Core Logic

**What it does:**
{EXPLAIN_CORE_SERVICE}

**Key methods:**
- `run()` - Main loop
- `process_data()` - Core processing
- `save_to_db()` - Database operations

## Execution Flow

### Scenario 1: {COMMON_USE_CASE}

**What happens step by step:**

1. **Trigger:** {WHAT_STARTS_THIS}
   ```python
   # services/main_service.py:45
   def run(self):
       while True:
           self.process_data()
   ```

2. **Fetch Data:** {FROM_WHERE}
   ```python
   # services/main_service.py:60
   def fetch_data(self):
       response = requests.get(self.api_url)
       return response.json()
   ```

3. **Process:** {WHAT_PROCESSING}
   ```python
   # services/main_service.py:80
   def process_data(self, data):
       # Transform and validate
       cleaned = self.clean(data)
       return cleaned
   ```

4. **Store:** {WHERE_STORED}
   ```python
   # services/main_service.py:100
   def save_to_db(self, data):
       self.db.insert(data)
   ```

5. **Complete:** {RESULT}

**Flow diagram:**
```mermaid
graph TB
    A[Trigger] --> B[Fetch from API]
    B --> C[Process/Clean Data]
    C --> D[Validate]
    D --> E{Valid?}
    E -->|Yes| F[Save to DB]
    E -->|No| G[Log Error]
    F --> H[Complete]
    G --> H
```

## Data Flow

### Input Data

**Format:**
```json
{
  "field1": "example",
  "field2": 123,
  "nested": {
    "key": "value"
  }
}
```

**Source:** {WHERE_FROM}

### Processing Steps

1. **Validation:** Check required fields
2. **Transformation:** Convert formats
3. **Enrichment:** Add calculated fields
4. **Cleaning:** Remove invalid data

### Output Data

**Format:**
```json
{
  "id": "uuid",
  "processed_field1": "value",
  "processed_field2": 456,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Destination:** {WHERE_TO}

## Important Functions

### Function 1: `process_data()`

**Purpose:** {WHAT_IT_DOES}

**Location:** `services/main_service.py:80`

**Parameters:**
- `data` (dict): Raw data from API
- `options` (dict): Processing options

**Returns:** Processed data (dict)

**Example:**
```python
result = process_data(
    data={"key": "value"},
    options={"validate": True}
)
```

### Function 2: `save_to_db()`

**Purpose:** Persist data to database

**Location:** `services/main_service.py:100`

**Error handling:**
- Retries 3 times on failure
- Logs errors
- Returns success status

## State Management

**How state is tracked:**
- Current job: In-memory variable
- Processing status: Database table
- Errors: Log files

**State transitions:**
```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Fetching: New job
    Fetching --> Processing: Data received
    Processing --> Saving: Processed
    Saving --> Complete: Success
    Saving --> Error: Failure
    Error --> Idle: Retry
    Complete --> [*]
```

## Error Handling

### Common Errors

**Error 1: API Connection Failed**
- **Cause:** Network issue or API down
- **Handled:** `services/main_service.py:65`
- **Recovery:** Retry with exponential backoff

**Error 2: Invalid Data Format**
- **Cause:** API response changed
- **Handled:** `services/main_service.py:85`
- **Recovery:** Log and skip record

**Error 3: Database Connection Lost**
- **Cause:** PostgreSQL restart or network
- **Handled:** `config.py:30`
- **Recovery:** Reconnect automatically

## Configuration

### Key Settings

**`API_URL`**
- **Type:** string
- **Default:** None (required)
- **Purpose:** Where to fetch data from
- **Example:** `https://api.example.com/data`

**`POLL_INTERVAL`**
- **Type:** integer (seconds)
- **Default:** 300
- **Purpose:** How often to check for new data
- **Example:** `60` (check every minute)

**`DATABASE_URL`**
- **Type:** string
- **Default:** None (required)
- **Purpose:** PostgreSQL connection string
- **Example:** `postgresql://user:pass@localhost/db`

## Performance

**Typical execution time:**
- Small dataset: ~2 seconds
- Large dataset: ~30 seconds

**Bottlenecks:**
- API response time: ~1-2 seconds
- Database writes: ~0.5 seconds per record
- Data processing: ~0.1 seconds per record

**Optimization strategies:**
- Batch database inserts (100 records at a time)
- Cache API responses (5 minute TTL)
- Async processing where possible

## Testing

**How to test manually:**
```bash
# 1. Set up test environment
export DATABASE_URL=postgresql://localhost/test_db

# 2. Run with sample data
python main.py --test-mode

# 3. Verify results
psql test_db -c "SELECT COUNT(*) FROM table_name"
```

**Automated tests:**
```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_service.py::test_process_data

# With coverage
pytest --cov=services tests/
```

## Debugging

**Enable debug logging:**
```bash
export LOG_LEVEL=DEBUG
python main.py
```

**Logs to check:**
```bash
tail -f logs/app.log
```

**Common debug scenarios:**

1. **Data not appearing in database:**
   - Check logs for errors: `grep ERROR logs/app.log`
   - Verify API connectivity: `curl $API_URL`
   - Check database connection: `psql $DATABASE_URL -c "SELECT 1"`

2. **Slow performance:**
   - Check API response time: Look for "Fetch took" in logs
   - Monitor database: `SELECT * FROM pg_stat_activity`
   - Profile code: `python -m cProfile main.py`
