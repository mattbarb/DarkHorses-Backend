#!/usr/bin/env python3
"""
DarkHorses Racing Odds API
FastAPI server providing access to live odds, historical odds, and statistics
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import json

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent.parent / '.env.local'
if not env_path.exists():
    env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

app = FastAPI(
    title="DarkHorses Racing Odds API",
    description="API for accessing live odds, historical odds, and statistics",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')

if not supabase_url or not supabase_key:
    raise ValueError("Missing Supabase credentials in environment")

supabase: Client = create_client(supabase_url, supabase_key)

# Mount static files for UI
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def read_root():
    """Serve the dashboard UI"""
    static_file = Path(__file__).parent / "static" / "index.html"
    if static_file.exists():
        return FileResponse(str(static_file))

    # Fallback to API info if UI not available
    return {
        "api": "DarkHorses Racing Odds API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "live_odds": "/api/live-odds",
            "historical_odds": "/api/historical-odds",
            "statistics": "/api/statistics",
            "scheduler_status": "/api/scheduler-status"
        }
    }


@app.get("/health")
def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/live-odds")
def get_live_odds(
    race_date: Optional[str] = Query(None, description="Filter by race date (YYYY-MM-DD)"),
    course: Optional[str] = Query(None, description="Filter by course name"),
    bookmaker: Optional[str] = Query(None, description="Filter by bookmaker name"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip")
):
    """
    Get live odds data

    Returns current odds from ra_odds_live table with optional filtering
    """
    try:
        query = supabase.table('ra_odds_live').select('*')

        # Apply filters
        if race_date:
            query = query.eq('race_date', race_date)
        if course:
            query = query.ilike('course', f'%{course}%')
        if bookmaker:
            query = query.ilike('bookmaker_name', f'%{bookmaker}%')

        # Apply pagination and ordering
        query = query.order('odds_timestamp', desc=True).range(offset, offset + limit - 1)

        result = query.execute()

        return {
            "success": True,
            "count": len(result.data),
            "limit": limit,
            "offset": offset,
            "data": result.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching live odds: {str(e)}")


@app.get("/api/live-odds/upcoming-races")
def get_upcoming_races(
    hours_ahead: int = Query(24, ge=1, le=168, description="Look ahead this many hours")
):
    """
    Get upcoming races with live odds

    Returns races scheduled within the next X hours
    """
    try:
        # Get distinct races from live odds
        today = date.today()
        tomorrow = today + timedelta(days=1)

        result = supabase.table('ra_odds_live')\
            .select('race_id, race_date, race_time, course, race_name')\
            .gte('race_date', str(today))\
            .lte('race_date', str(tomorrow))\
            .execute()

        # Get unique races
        races = {}
        if result.data:
            for record in result.data:
                race_id = record.get('race_id')
                if race_id and race_id not in races:
                    races[race_id] = record

        return {
            "success": True,
            "count": len(races),
            "data": list(races.values())
        }

    except Exception as e:
        logger.error(f"Error fetching upcoming races: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching upcoming races: {str(e)}")


@app.get("/api/historical-odds")
def get_historical_odds(
    race_date: Optional[str] = Query(None, description="Filter by race date (YYYY-MM-DD)"),
    course: Optional[str] = Query(None, description="Filter by course name"),
    year: Optional[int] = Query(None, ge=2015, le=2025, description="Filter by year"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip")
):
    """
    Get historical odds data

    Returns historical odds from rb_odds_historical table with optional filtering
    """
    try:
        query = supabase.table('rb_odds_historical').select('*')

        # Apply filters
        if race_date:
            query = query.eq('race_date', race_date)
        if course:
            query = query.ilike('course', f'%{course}%')
        if year:
            query = query.gte('race_date', f'{year}-01-01').lte('race_date', f'{year}-12-31')

        # Apply pagination and ordering
        query = query.order('race_date', desc=True).range(offset, offset + limit - 1)

        result = query.execute()

        return {
            "success": True,
            "count": len(result.data) if result.data else 0,
            "limit": limit,
            "offset": offset,
            "data": result.data if result.data else [],
            "message": "No historical data available yet" if not result.data else None
        }

    except Exception as e:
        logger.error(f"Error fetching historical odds: {str(e)}")
        # Return empty result instead of error if table doesn't exist yet
        return {
            "success": True,
            "count": 0,
            "limit": limit,
            "offset": offset,
            "data": [],
            "message": "Historical odds data not available - table may not exist yet or scheduler hasn't run"
        }


@app.get("/api/statistics")
def get_statistics(
    table: str = Query("all", description="Which stats to return: 'live', 'historical', or 'all'")
):
    """
    Get latest statistics

    Returns statistics from JSON files generated by the stats tracker
    """
    try:
        stats_dir = Path(__file__).parent / 'odds_statistics' / 'output'

        result = {}

        if table in ['live', 'all']:
            live_file = stats_dir / 'live_stats_latest.json'
            if live_file.exists():
                with open(live_file, 'r') as f:
                    result['live'] = json.load(f)

        if table in ['historical', 'all']:
            historical_file = stats_dir / 'historical_stats_latest.json'
            if historical_file.exists():
                with open(historical_file, 'r') as f:
                    result['historical'] = json.load(f)

        if table == 'all':
            all_file = stats_dir / 'all_stats_latest.json'
            if all_file.exists():
                with open(all_file, 'r') as f:
                    result['combined'] = json.load(f)

        # Return empty structure if no files exist yet (scheduler hasn't run)
        if not result:
            logger.warning("Statistics files not found - scheduler may not have run yet")
            return {
                "success": True,
                "data": {},
                "message": "Statistics not available yet - data collection in progress"
            }

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Error loading statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading statistics: {str(e)}")


@app.get("/api/scheduler-status")
def get_scheduler_status():
    """
    Get scheduler status and configuration

    Returns information about scheduled tasks and their timing
    """
    # Try to load real-time status from scheduler
    status_file = Path(__file__).parent / 'logs' / 'scheduler_status.json'
    live_status = {}

    try:
        if status_file.exists():
            with open(status_file, 'r') as f:
                live_status = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load scheduler status: {e}")

    return {
        "success": True,
        "schedulers": {
            "live_odds": {
                "name": "Live Odds Fetcher",
                "schedule": "ADAPTIVE (10s-15min based on race proximity)",
                "description": "Fetches live odds for today and tomorrow's races with smart scheduling",
                "details": {
                    "adaptive_intervals": {
                        "imminent": "10 seconds (race <5 min away)",
                        "soon": "60 seconds (race <30 min away)",
                        "upcoming": "5 minutes (race <2 hours away)",
                        "default": "15 minutes (checking for races)"
                    },
                    "coverage": "Today + Tomorrow (GB & IRE races)",
                    "stop_updating": "When race starts",
                    "tables": ["ra_odds_live"]
                },
                "last_run": live_status.get("live_odds", {}).get("last_run"),
                "last_success": live_status.get("live_odds", {}).get("last_success"),
                "next_check": live_status.get("live_odds", {}).get("next_check"),
                "next_interval": live_status.get("live_odds", {}).get("next_interval"),
                "status": live_status.get("live_odds", {}).get("status", "unknown")
            },
            "historical_odds": {
                "name": "Historical Odds Fetcher",
                "schedule": "Daily at 1:00 AM UK time",
                "description": "Fetches yesterday's final odds and results",
                "details": {
                    "daily_fetch": "1:00 AM UK time",
                    "coverage": "GB & IRE races from 2015 onwards",
                    "data_includes": "Final odds, results, and race metadata",
                    "tables": ["rb_odds_historical"]
                },
                "last_run": live_status.get("historical_odds", {}).get("last_run"),
                "last_success": live_status.get("historical_odds", {}).get("last_success"),
                "status": live_status.get("historical_odds", {}).get("status", "unknown")
            },
            "statistics_updater": {
                "name": "Statistics Tracker",
                "schedule": "Every 10 minutes",
                "description": "Updates statistics after live/historical fetches",
                "details": {
                    "frequency": "Every 10 minutes",
                    "output_location": "odds_statistics/output/",
                    "files_generated": [
                        "live_stats_latest.json",
                        "historical_stats_latest.json",
                        "all_stats_latest.json"
                    ],
                    "manual_run": "python3 odds_statistics/update_stats.py"
                },
                "last_run": live_status.get("statistics", {}).get("last_run"),
                "last_success": live_status.get("statistics", {}).get("last_success"),
                "status": live_status.get("statistics", {}).get("status", "unknown")
            }
        },
        "system_info": {
            "timezone": "UK Time (GMT/BST)",
            "database": "Supabase PostgreSQL",
            "api_source": "Racing API (racingapi.com)",
            "regions_covered": ["GB", "IRE"]
        }
    }


@app.get("/api/bookmakers")
def get_bookmakers():
    """
    Get list of all bookmakers in the system
    """
    try:
        # Get unique bookmakers from live odds
        result = supabase.table('ra_odds_live')\
            .select('bookmaker_id, bookmaker_name, bookmaker_type')\
            .execute()

        # Get unique bookmakers
        bookmakers = {}
        for record in result.data:
            bm_id = record['bookmaker_id']
            if bm_id not in bookmakers:
                bookmakers[bm_id] = {
                    'id': record['bookmaker_id'],
                    'name': record['bookmaker_name'],
                    'type': record['bookmaker_type']
                }

        return {
            "success": True,
            "count": len(bookmakers),
            "data": list(bookmakers.values())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bookmakers: {str(e)}")


@app.get("/api/courses")
def get_courses():
    """
    Get list of all courses/tracks in the system
    """
    try:
        # Get unique courses from live odds
        result = supabase.table('ra_odds_live')\
            .select('course')\
            .execute()

        # Get unique courses
        courses = {}
        for record in result.data:
            course = record.get('course')
            if course and course not in courses:
                courses[course] = {
                    'name': course
                }

        return {
            "success": True,
            "count": len(courses),
            "data": list(courses.values())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching courses: {str(e)}")


@app.get("/api/historical-odds/summary")
def get_historical_summary():
    """
    Get summary statistics for historical odds table
    """
    try:
        logger.info("Fetching historical odds summary...")

        # Get total count - using proper supabase-py v2 syntax
        count_result = supabase.table('rb_odds_historical')\
            .select('*', count='exact')\
            .limit(1)\
            .execute()

        # Log the response structure for debugging
        logger.info(f"Count result type: {type(count_result)}")
        logger.info(f"Count result attributes: {dir(count_result)}")

        # Try different ways to access count
        total_count = 0
        if hasattr(count_result, 'count'):
            total_count = count_result.count
            logger.info(f"Got count from .count attribute: {total_count}")
        elif hasattr(count_result, 'headers') and 'content-range' in count_result.headers:
            # Parse from content-range header: "0-999/1234"
            content_range = count_result.headers.get('content-range', '')
            if '/' in content_range:
                total_count = int(content_range.split('/')[-1])
                logger.info(f"Got count from content-range header: {total_count}")
        else:
            # Fallback: count the data we get back
            logger.warning("Could not find count, using data length as estimate")
            total_count = len(count_result.data) if count_result.data else 0

        logger.info(f"Final total_count: {total_count}")

        # Get date range
        date_result = supabase.table('rb_odds_historical')\
            .select('race_date')\
            .order('race_date', desc=False)\
            .limit(1)\
            .execute()

        earliest_date = date_result.data[0]['race_date'] if date_result.data else None
        logger.info(f"Earliest date: {earliest_date}")

        latest_result = supabase.table('rb_odds_historical')\
            .select('race_date')\
            .order('race_date', desc=True)\
            .limit(1)\
            .execute()

        latest_date = latest_result.data[0]['race_date'] if latest_result.data else None
        logger.info(f"Latest date: {latest_date}")

        # Get unique races count (approximate - sample first 10k)
        races_result = supabase.table('rb_odds_historical')\
            .select('race_id')\
            .limit(10000)\
            .execute()

        unique_races = len(set([r['race_id'] for r in races_result.data])) if races_result.data else 0
        logger.info(f"Unique races (sample): {unique_races}")

        return {
            "success": True,
            "total_records": total_count,
            "earliest_date": earliest_date,
            "latest_date": latest_date,
            "unique_races_sample": unique_races,
            "date_range": f"{earliest_date[:4] if earliest_date else '?'} - {latest_date[:4] if latest_date else '?'}"
        }

    except Exception as e:
        logger.error(f"Error fetching historical summary: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "total_records": 0,
            "message": f"Error: {str(e)}"
        }


@app.get("/api/live-odds/next-race")
def get_next_race():
    """
    Get information about the next upcoming race and today's race schedule
    """
    try:
        from datetime import datetime, timezone
        import pytz

        uk_tz = pytz.timezone('Europe/London')
        now = datetime.now(uk_tz)
        today = now.date()

        # Get all distinct races for today with their off times
        result = supabase.table('ra_odds_live')\
            .select('race_id, race_date, race_time, off_dt, course, race_name')\
            .eq('race_date', str(today))\
            .execute()

        if not result.data:
            return {
                "success": True,
                "next_race": None,
                "races_today": [],
                "total_races_today": 0,
                "message": "No races scheduled for today"
            }

        # Get unique races and calculate time until each
        races_map = {}
        for record in result.data:
            race_id = record.get('race_id')
            if race_id and race_id not in races_map:
                races_map[race_id] = record

        races = list(races_map.values())

        # Calculate time until race for each
        upcoming_races = []
        for race in races:
            off_dt = race.get('off_dt')
            if off_dt:
                try:
                    # Parse race time
                    from dateutil import parser as date_parser
                    race_time = date_parser.parse(off_dt)

                    # Calculate minutes until race
                    time_until = (race_time - now).total_seconds() / 60

                    race_info = {
                        'race_id': race.get('race_id'),
                        'course': race.get('course'),
                        'race_name': race.get('race_name'),
                        'race_time': race.get('race_time'),
                        'off_dt': off_dt,
                        'minutes_until': round(time_until, 1),
                        'started': time_until < 0
                    }

                    upcoming_races.append(race_info)
                except Exception as e:
                    logger.warning(f"Error parsing race time for {race.get('race_id')}: {e}")

        # Sort by time
        upcoming_races.sort(key=lambda x: x['minutes_until'])

        # Find next race (first one that hasn't started)
        next_race = None
        for race in upcoming_races:
            if not race['started']:
                next_race = race
                break

        # Determine current adaptive interval
        adaptive_interval = "15 minutes (default)"
        if next_race:
            mins = next_race['minutes_until']
            if mins <= 5:
                adaptive_interval = "10 seconds (imminent)"
            elif mins <= 30:
                adaptive_interval = "60 seconds (soon)"
            elif mins <= 120:
                adaptive_interval = "5 minutes (upcoming)"

        return {
            "success": True,
            "next_race": next_race,
            "races_today": upcoming_races[:10],  # Limit to first 10
            "total_races_today": len(upcoming_races),
            "races_finished": len([r for r in upcoming_races if r['started']]),
            "races_upcoming": len([r for r in upcoming_races if not r['started']]),
            "current_interval": adaptive_interval
        }

    except Exception as e:
        logger.error(f"Error fetching next race: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching next race: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
