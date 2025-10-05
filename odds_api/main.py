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
import psycopg2
from psycopg2.extras import RealDictCursor

# Setup logging
logger = logging.getLogger('API')  # Clear service name

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

# Get DATABASE_URL for direct PostgreSQL queries
database_url = os.getenv('DATABASE_URL')

# Helper function for direct PostgreSQL count queries
def get_direct_postgres_count(table_name: str) -> int:
    """Get count using direct PostgreSQL connection (more reliable than Supabase count)"""
    if not database_url:
        logger.warning("DATABASE_URL not set, cannot use direct PostgreSQL queries")
        return 0

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Error getting direct PostgreSQL count: {e}")
        return 0

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


@app.get("/version")
def version_check():
    """Deployment version check - verify which code is running"""
    return {
        "service": "DarkHorses Odds API",
        "version": "1.0.0",
        "deployed_at": datetime.now().isoformat(),
        "historical_table_columns": "date_of_race, track (NOT race_date, course)",
        "logger_names": "API, SCHEDULER, LIVE_ODDS, HISTORICAL_ODDS",
        "git_commit": "Fix historical column names + clear service logging",
        "checks": {
            "database_url_configured": bool(database_url),
            "supabase_configured": bool(supabase_url),
            "historical_table": "rb_odds_historical (date_of_race, track, race_time)"
        }
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


@app.get("/api/live-odds/races-by-stage")
def get_races_by_stage():
    """
    Get races organized by schedule stage (Kanban board)

    Returns races grouped into 4 stages:
    - early_market: >2 hours away
    - pre_race: 30min-2hrs away
    - going_to_post: 5-30min away
    - at_post: <5min away
    """
    try:
        from datetime import datetime, timezone

        # Get races that haven't started yet (off_dt in the future)
        now = datetime.now(timezone.utc)

        # Query for races with off_dt >= now (upcoming races only)
        result = supabase.table('ra_odds_live')\
            .select('race_id, race_date, race_time, off_dt, course, race_name, race_type, distance, runners')\
            .gte('off_dt', now.isoformat())\
            .execute()

        # Get unique races and calculate minutes until
        races_map = {}

        if result.data:
            for record in result.data:
                race_id = record.get('race_id')
                if race_id and race_id not in races_map:
                    # Calculate minutes until race
                    off_dt = record.get('off_dt')
                    minutes_until = None
                    if off_dt:
                        try:
                            race_time = datetime.fromisoformat(off_dt.replace('Z', '+00:00'))
                            minutes_until = (race_time - now).total_seconds() / 60
                        except:
                            pass

                    races_map[race_id] = {
                        **record,
                        'minutes_until': minutes_until,
                        'runners_data': []  # Will populate with runner info
                    }

        # Fetch runner data and timestamps for each race
        for race_id in races_map.keys():
            try:
                # Get all odds for this race, grouped by horse
                runners_result = supabase.table('ra_odds_live')\
                    .select('horse_id, horse_name, horse_number, odds_fractional, odds_decimal, bookmaker_name, odds_timestamp, fetched_at')\
                    .eq('race_id', race_id)\
                    .execute()

                # Find the most recent update timestamp for this race
                latest_timestamp = None
                if runners_result.data:
                    for odds_record in runners_result.data:
                        timestamp = odds_record.get('odds_timestamp') or odds_record.get('fetched_at')
                        if timestamp:
                            try:
                                ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                if latest_timestamp is None or ts > latest_timestamp:
                                    latest_timestamp = ts
                            except:
                                pass

                    # Store the latest timestamp
                    if latest_timestamp:
                        races_map[race_id]['last_updated'] = latest_timestamp.isoformat()

                if runners_result.data:
                    # Group by horse_id to get best odds per horse
                    horses = {}
                    for odds_record in runners_result.data:
                        horse_id = odds_record.get('horse_id')
                        if not horse_id:
                            continue

                        if horse_id not in horses:
                            horses[horse_id] = {
                                'horse_id': horse_id,
                                'horse_name': odds_record.get('horse_name'),
                                'horse_number': odds_record.get('horse_number'),
                                'best_odds_fractional': odds_record.get('odds_fractional'),
                                'best_odds_decimal': odds_record.get('odds_decimal'),
                                'best_bookmaker': odds_record.get('bookmaker_name'),
                                'all_odds': []
                            }

                        # Track all bookmaker odds for this horse
                        if odds_record.get('odds_decimal'):
                            horses[horse_id]['all_odds'].append({
                                'bookmaker': odds_record.get('bookmaker_name'),
                                'odds_fractional': odds_record.get('odds_fractional'),
                                'odds_decimal': odds_record.get('odds_decimal')
                            })

                            # Update best odds (lowest decimal = shortest odds = favorite)
                            current_best = horses[horse_id]['best_odds_decimal']
                            new_odds = odds_record.get('odds_decimal')
                            if current_best is None or (new_odds and new_odds < current_best):
                                horses[horse_id]['best_odds_decimal'] = new_odds
                                horses[horse_id]['best_odds_fractional'] = odds_record.get('odds_fractional')
                                horses[horse_id]['best_bookmaker'] = odds_record.get('bookmaker_name')

                    # Convert to list and sort by odds (favorites first)
                    runners_list = list(horses.values())
                    runners_list.sort(key=lambda x: x.get('best_odds_decimal') or 999)

                    # Mark favorite (horse with lowest odds)
                    if runners_list:
                        runners_list[0]['is_favorite'] = True

                    races_map[race_id]['runners_data'] = runners_list

            except Exception as runner_error:
                logger.warning(f"Error fetching runners for race {race_id}: {runner_error}")
                # Continue without runner data for this race
                pass

        # Calculate next phase transition for each race
        for race_id, race in races_map.items():
            mins = race.get('minutes_until')
            if mins is not None and mins >= 0:
                # Calculate when race moves to next phase
                next_phase_minutes = None
                next_phase_name = None

                if mins >= 120:  # Currently in Early Market
                    next_phase_minutes = mins - 120
                    next_phase_name = "Pre Race"
                elif mins >= 30:  # Currently in Pre Race
                    next_phase_minutes = mins - 30
                    next_phase_name = "Going To Post"
                elif mins >= 5:  # Currently in Going To Post
                    next_phase_minutes = mins - 5
                    next_phase_name = "At Post"
                else:  # At Post
                    next_phase_minutes = mins
                    next_phase_name = "Race Start"

                if next_phase_minutes is not None:
                    next_phase_time = now + timedelta(minutes=next_phase_minutes)
                    races_map[race_id]['next_phase_time'] = next_phase_time.isoformat()
                    races_map[race_id]['next_phase_name'] = next_phase_name
                    races_map[race_id]['next_phase_minutes'] = round(next_phase_minutes, 1)

        # Categorize races by stage (no finished races - only upcoming)
        stages = {
            'at_post': [],        # <5 min
            'going_to_post': [],  # 5-30 min
            'pre_race': [],       # 30min-2hrs
            'early_market': [],   # >2hrs
        }

        for race in races_map.values():
            mins = race.get('minutes_until')
            if mins is None or mins < 0:
                continue  # Skip races without timing or that somehow slipped through

            if mins < 5:
                stages['at_post'].append(race)
            elif mins < 30:
                stages['going_to_post'].append(race)
            elif mins < 120:
                stages['pre_race'].append(race)
            else:
                stages['early_market'].append(race)

        # Sort each stage by time (soonest first)
        for stage in stages.values():
            stage.sort(key=lambda x: x.get('minutes_until', 999))

        return {
            "success": True,
            "stages": stages,
            "total_races": len(races_map),
            "timestamp": now.isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching races by stage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching races by stage: {str(e)}")


@app.get("/api/historical-odds")
def get_historical_odds(
    race_date: Optional[str] = Query(None, description="Filter by race date (YYYY-MM-DD)"),
    course: Optional[str] = Query(None, description="Filter by course name (track)"),
    year: Optional[int] = Query(None, ge=2015, le=2025, description="Filter by year"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip")
):
    """
    Get historical odds data

    Returns historical odds from rb_odds_historical table with optional filtering
    Note: rb_odds_historical uses 'date_of_race' and 'track' (not 'race_date' and 'course')
    """
    try:
        query = supabase.table('rb_odds_historical').select('*')

        # Apply filters (use correct column names: date_of_race, track)
        if race_date:
            query = query.eq('date_of_race', race_date)
        if course:
            query = query.ilike('track', f'%{course}%')
        if year:
            query = query.gte('date_of_race', f'{year}-01-01').lte('date_of_race', f'{year}-12-31')

        # Apply pagination and ordering
        query = query.order('date_of_race', desc=True).range(offset, offset + limit - 1)

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


@app.post("/api/statistics/refresh")
def refresh_statistics():
    """
    Manually trigger statistics collection

    Useful for testing or forcing an immediate update
    """
    try:
        logger.info("📊 Manual statistics refresh requested")

        # Import the update function
        import sys
        stats_path = Path(__file__).parent / 'odds_statistics'
        sys.path.insert(0, str(stats_path))

        from update_stats import update_all_statistics
        from config import Config

        logger.info(f"📍 Config.DATABASE_URL set: {bool(Config.DATABASE_URL)}")

        # Mask password for logging
        if Config.DATABASE_URL and '@' in Config.DATABASE_URL:
            parts = Config.DATABASE_URL.split('@')
            masked_url = f"***@{parts[1]}"
            logger.info(f"📍 Using URL: {masked_url}")

        logger.info("📍 Calling update_all_statistics()...")
        result = update_all_statistics(save_to_file=True)

        if result:
            logger.info(f"✅ Statistics refresh completed - {len(result)} keys")

            # Check if files were actually created
            output_dir = Path(Config.DEFAULT_OUTPUT_DIR)
            files_created = []
            if output_dir.exists():
                files_created = [f.name for f in output_dir.iterdir() if f.is_file()]

            return {
                "success": True,
                "message": "Statistics updated successfully",
                "timestamp": result.get('timestamp'),
                "tables_updated": list(result.keys()),
                "output_directory": str(output_dir),
                "directory_exists": output_dir.exists(),
                "files_created": files_created
            }
        else:
            logger.error("❌ Statistics refresh returned empty result")

            # Try to get more diagnostic info
            try:
                from database import DatabaseConnection
                db = DatabaseConnection(database_url)
                db.connect()
                db.disconnect()
                db_test = "Database connection successful"
            except Exception as db_e:
                db_test = f"Database connection failed: {str(db_e)}"

            return {
                "success": False,
                "message": "Statistics update returned empty result",
                "diagnostic": {
                    "database_url_set": bool(database_url),
                    "config_database_url_set": bool(Config.DATABASE_URL),
                    "database_test": db_test,
                    "stats_path": str(stats_path),
                    "output_dir": Config.DEFAULT_OUTPUT_DIR
                }
            }

    except Exception as e:
        logger.error(f"❌ Manual statistics refresh failed: {e}")
        import traceback
        tb = traceback.format_exc()
        logger.error(tb)
        return {
            "success": False,
            "message": f"Statistics refresh exception: {str(e)}",
            "traceback": tb
        }


@app.get("/api/statistics/config-check")
def check_statistics_config():
    """
    Check which database URL the statistics module is using
    """
    import sys
    from pathlib import Path

    try:
        stats_path = Path(__file__).parent / 'odds_statistics'
        sys.path.insert(0, str(stats_path))
        from config import Config

        # Mask passwords in URLs
        def mask_url(url):
            if not url:
                return None
            if '@' in url:
                parts = url.split('@')
                # Show everything after @ (host), mask before
                return f"postgresql://***:***@{parts[1]}"
            return url[:30] + "..."

        return {
            "success": True,
            "environment_variables": {
                "SESSION_POOLER": bool(os.getenv('SESSION_POOLER')),
                "TRANSACTION_POOLER": bool(os.getenv('TRANSACTION_POOLER')),
                "DATABASE_URL": bool(os.getenv('DATABASE_URL'))
            },
            "config_resolved": {
                "DATABASE_URL": mask_url(Config.DATABASE_URL),
                "uses_pooler": "pooler.supabase.com" in (Config.DATABASE_URL or ""),
                "uses_direct_db": "db." in (Config.DATABASE_URL or "") and ".supabase.co" in (Config.DATABASE_URL or "")
            },
            "resolution_order": [
                "1. SESSION_POOLER (preferred)",
                "2. TRANSACTION_POOLER (fallback)",
                "3. DATABASE_URL (last resort)"
            ]
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.get("/api/statistics/test-ipv4")
def test_ipv4_resolution():
    """
    Test IPv4 resolution for database connection

    Returns captured log messages to diagnose IPv6 issues
    """
    import io
    import logging as log_module

    # Create string buffer to capture logs
    log_buffer = io.StringIO()
    handler = log_module.StreamHandler(log_buffer)
    handler.setLevel(log_module.INFO)
    formatter = log_module.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # Add handler to STATISTICS_DB logger
    test_logger = log_module.getLogger('STATISTICS_DB')
    test_logger.addHandler(handler)
    test_logger.setLevel(log_module.INFO)

    try:
        database_url = os.getenv('DATABASE_URL')

        if not database_url:
            return {
                "success": False,
                "message": "DATABASE_URL not set"
            }

        # Import and test
        import sys
        stats_path = Path(__file__).parent / 'odds_statistics'
        sys.path.insert(0, str(stats_path))

        from database import DatabaseConnection

        # This should trigger IPv4 resolution logging
        db = DatabaseConnection(database_url)

        # Get the logs
        log_output = log_buffer.getvalue()

        # Try to connect
        connection_result = "Not attempted"
        connection_error = None
        try:
            db.connect()
            connection_result = "Success"
            db.disconnect()
        except Exception as e:
            connection_result = "Failed"
            connection_error = str(e)

        # Also test direct psycopg2 connection without IPv4 resolution
        direct_test_result = "Not attempted"
        direct_test_error = None
        try:
            import psycopg2
            logger.info("Testing direct psycopg2 connection (no IPv4 resolution)...")
            direct_conn = psycopg2.connect(database_url)
            direct_test_result = "Success"
            direct_conn.close()
        except Exception as direct_e:
            direct_test_result = "Failed"
            direct_test_error = str(direct_e)

        return {
            "success": True,
            "ipv4_resolution_logs": log_output.split('\n') if log_output else ["No logs captured"],
            "with_ipv4_resolution": {
                "result": connection_result,
                "error": connection_error[:200] if connection_error else None
            },
            "direct_connection_test": {
                "result": direct_test_result,
                "error": direct_test_error[:200] if direct_test_error else None,
                "note": "Tests if IPv6 connections work on Render"
            },
            "resolved_connection_string_preview": db.connection_string[:60] + "..." if len(db.connection_string) > 60 else db.connection_string[:30] + "..."
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "logs": log_buffer.getvalue()
        }
    finally:
        test_logger.removeHandler(handler)


@app.get("/api/statistics/debug")
def debug_statistics_files():
    """
    Debug endpoint to check file system and statistics files

    Shows where files should be and what actually exists
    """
    try:
        import os
        from pathlib import Path

        debug_info = {
            "current_working_directory": os.getcwd(),
            "main_py_location": str(Path(__file__).parent),
            "expected_stats_dir": str(Path(__file__).parent / 'odds_statistics' / 'output'),
            "stats_dir_exists": False,
            "files_found": [],
            "directory_listing": []
        }

        # Check if stats directory exists
        stats_dir = Path(__file__).parent / 'odds_statistics' / 'output'
        debug_info["stats_dir_exists"] = stats_dir.exists()

        if stats_dir.exists():
            # List all files in the directory
            debug_info["files_found"] = [f.name for f in stats_dir.iterdir() if f.is_file()]
            debug_info["directory_listing"] = [
                {
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                }
                for f in stats_dir.iterdir() if f.is_file()
            ]
        else:
            # Check if parent directory exists
            parent_dir = Path(__file__).parent / 'odds_statistics'
            debug_info["odds_statistics_dir_exists"] = parent_dir.exists()

            if parent_dir.exists():
                debug_info["odds_statistics_contents"] = [f.name for f in parent_dir.iterdir()]

        # Check from config perspective
        try:
            import sys
            stats_path = Path(__file__).parent / 'odds_statistics'
            sys.path.insert(0, str(stats_path))
            from config import Config

            debug_info["config_output_dir"] = Config.DEFAULT_OUTPUT_DIR
            debug_info["config_dir_exists"] = Path(Config.DEFAULT_OUTPUT_DIR).exists()

            if Path(Config.DEFAULT_OUTPUT_DIR).exists():
                debug_info["config_dir_files"] = [
                    f.name for f in Path(Config.DEFAULT_OUTPUT_DIR).iterdir() if f.is_file()
                ]
        except Exception as e:
            debug_info["config_error"] = str(e)

        return {
            "success": True,
            "debug_info": debug_info
        }

    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.get("/api/scheduler-health")
def get_scheduler_health():
    """
    Check if scheduler thread is alive and running
    """
    import threading

    # Get all threads
    threads = threading.enumerate()
    scheduler_threads = [t for t in threads if 'scheduler' in t.name.lower() or t.name == 'Thread-1']

    return {
        "total_threads": len(threads),
        "scheduler_threads_found": len(scheduler_threads),
        "thread_names": [t.name for t in threads],
        "scheduler_thread_alive": len(scheduler_threads) > 0,
        "scheduler_threads": [
            {
                "name": t.name,
                "alive": t.is_alive(),
                "daemon": t.daemon,
                "ident": t.ident
            }
            for t in scheduler_threads
        ]
    }


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


@app.get("/api/historical-odds/debug")
def debug_historical_summary():
    """Debug endpoint to see why count is failing"""
    debug_info = {
        "database_url_configured": bool(database_url),
        "supabase_url_configured": bool(supabase_url),
        "errors": []
    }

    # Test direct PostgreSQL
    if database_url:
        try:
            import socket
            import re
            # Force IPv4 like we do in statistics module
            match = re.search(r'@([^:/?]+)', database_url)
            if match:
                hostname = match.group(1)
                addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
                ipv4 = addr_info[0][4][0] if addr_info else None
                debug_info["hostname"] = hostname
                debug_info["ipv4_resolved"] = ipv4

                # Try connection with IPv4
                ipv4_url = database_url.replace(hostname, ipv4) if ipv4 else database_url
                conn = psycopg2.connect(ipv4_url)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM rb_odds_historical")
                count = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                debug_info["postgresql_count"] = count
                debug_info["postgresql_success"] = True
        except Exception as e:
            debug_info["postgresql_error"] = str(e)
            debug_info["postgresql_success"] = False
            import traceback
            debug_info["postgresql_traceback"] = traceback.format_exc()

    # Test Supabase API
    try:
        result = supabase.table('rb_odds_historical').select('*', count='exact').limit(1).execute()
        debug_info["supabase_count"] = getattr(result, 'count', None)
        debug_info["supabase_has_data"] = bool(result.data)
        debug_info["supabase_data_length"] = len(result.data) if result.data else 0
    except Exception as e:
        debug_info["supabase_error"] = str(e)

    return debug_info


@app.get("/api/historical-odds/summary")
def get_historical_summary():
    """
    Get summary statistics for historical odds table
    """
    try:
        logger.info("Fetching historical odds summary...")

        # Apply IPv4 fix for DATABASE_URL (same as statistics module)
        total_count = 0
        if database_url:
            try:
                import socket
                import re
                # Force IPv4 connection
                match = re.search(r'@([^:/?]+)', database_url)
                if match:
                    hostname = match.group(1)
                    logger.info(f"Resolving {hostname} to IPv4...")
                    addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
                    if addr_info:
                        ipv4_address = addr_info[0][4][0]
                        logger.info(f"Resolved to IPv4: {ipv4_address}")
                        ipv4_url = database_url.replace(hostname, ipv4_address)

                        conn = psycopg2.connect(ipv4_url)
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM rb_odds_historical")
                        total_count = cursor.fetchone()[0]
                        cursor.close()
                        conn.close()
                        logger.info(f"Direct PostgreSQL count: {total_count}")
            except Exception as e:
                logger.error(f"PostgreSQL count failed: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # If direct count failed, try Supabase API
        if total_count == 0:
            logger.info("Direct count was 0, trying Supabase API...")
            count_result = supabase.table('rb_odds_historical')\
                .select('*', count='exact')\
                .limit(1)\
                .execute()

            # Try different ways to access count
            if hasattr(count_result, 'count'):
                total_count = count_result.count
                logger.info(f"Got count from .count attribute: {total_count}")

        logger.info(f"Final total_count: {total_count}")

        # Get date range (column is 'date_of_race' not 'race_date')
        date_result = supabase.table('rb_odds_historical')\
            .select('date_of_race')\
            .order('date_of_race', desc=False)\
            .limit(1)\
            .execute()

        earliest_date = date_result.data[0]['date_of_race'] if date_result.data else None
        logger.info(f"Earliest date: {earliest_date}")

        latest_result = supabase.table('rb_odds_historical')\
            .select('date_of_race')\
            .order('date_of_race', desc=True)\
            .limit(1)\
            .execute()

        latest_date = latest_result.data[0]['date_of_race'] if latest_result.data else None
        logger.info(f"Latest date: {latest_date}")

        # Get unique races count (approximate - sample first 10k by date+track+time combo)
        # Note: rb_odds_historical doesn't have race_id, use combination of date, track, time
        races_result = supabase.table('rb_odds_historical')\
            .select('date_of_race, track, race_time')\
            .limit(10000)\
            .execute()

        unique_races = 0
        if races_result.data:
            # Count unique combinations of date+track+time
            race_combos = set()
            for r in races_result.data:
                combo = (r.get('date_of_race'), r.get('track'), r.get('race_time'))
                race_combos.add(combo)
            unique_races = len(race_combos)

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
