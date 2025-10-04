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
            .select('race_id, race_date, race_time, course, country, race_name')\
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
            "count": len(result.data),
            "limit": limit,
            "offset": offset,
            "data": result.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching historical odds: {str(e)}")


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
                "schedule": "Every 5 minutes",
                "description": "Fetches live odds for today and tomorrow's races",
                "details": {
                    "frequency": "5 minutes default",
                    "coverage": "Today + Tomorrow (GB & IRE races)",
                    "stop_updating": "When race starts",
                    "tables": ["ra_odds_live"]
                },
                "last_run": live_status.get("live_odds", {}).get("last_run"),
                "last_success": live_status.get("live_odds", {}).get("last_success"),
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
            .select('course, country')\
            .execute()

        # Get unique courses
        courses = {}
        for record in result.data:
            course = record['course']
            if course and course not in courses:
                courses[course] = {
                    'name': course,
                    'country': record['country']
                }

        return {
            "success": True,
            "count": len(courses),
            "data": list(courses.values())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching courses: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
