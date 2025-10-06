#!/usr/bin/env python3
"""
Racing API Masters - Web Service
FastAPI service to expose racing data from Supabase
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import os
from datetime import date, datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent / '.env.local'
if env_path.exists():
    load_dotenv(env_path)

# Initialize FastAPI
app = FastAPI(
    title="Racing API Masters",
    description="UK & Ireland Racing Data API - Courses, Horses, Jockeys, Trainers, Races & Results",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """Get database connection"""
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Database URL not configured")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Racing API Masters",
        "version": "1.0.0",
        "description": "UK & Ireland Racing Data API",
        "docs": "/docs",
        "endpoints": {
            "courses": "/courses",
            "bookmakers": "/bookmakers",
            "jockeys": "/jockeys",
            "trainers": "/trainers",
            "owners": "/owners",
            "horses": "/horses",
            "races": "/races",
            "runners": "/runners",
            "results": "/results",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


# ============================================================================
# COURSES
# ============================================================================

@app.get("/courses")
async def get_courses(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    region: Optional[str] = None,
    name: Optional[str] = None
):
    """Get racing courses"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM ra_courses WHERE 1=1"
    params = []

    if region:
        query += " AND region_code = %s"
        params.append(region.upper())

    if name:
        query += " AND name ILIKE %s"
        params.append(f"%{name}%")

    query += " ORDER BY name LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"count": len(results), "data": results}


@app.get("/courses/{course_id}")
async def get_course(course_id: int):
    """Get specific course by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ra_courses WHERE course_id = %s", (course_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Course not found")

    return result


# ============================================================================
# BOOKMAKERS
# ============================================================================

@app.get("/bookmakers")
async def get_bookmakers(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get bookmakers"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM ra_bookmakers ORDER BY name LIMIT %s OFFSET %s",
        (limit, offset)
    )
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"count": len(results), "data": results}


# ============================================================================
# JOCKEYS
# ============================================================================

@app.get("/jockeys")
async def get_jockeys(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    name: Optional[str] = None
):
    """Get jockeys"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM ra_jockeys WHERE 1=1"
    params = []

    if name:
        query += " AND name ILIKE %s"
        params.append(f"%{name}%")

    query += " ORDER BY name LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"count": len(results), "data": results}


@app.get("/jockeys/{jockey_id}")
async def get_jockey(jockey_id: int):
    """Get specific jockey by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ra_jockeys WHERE jockey_id = %s", (jockey_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Jockey not found")

    return result


# ============================================================================
# TRAINERS
# ============================================================================

@app.get("/trainers")
async def get_trainers(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    name: Optional[str] = None
):
    """Get trainers"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM ra_trainers WHERE 1=1"
    params = []

    if name:
        query += " AND name ILIKE %s"
        params.append(f"%{name}%")

    query += " ORDER BY name LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"count": len(results), "data": results}


@app.get("/trainers/{trainer_id}")
async def get_trainer(trainer_id: int):
    """Get specific trainer by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ra_trainers WHERE trainer_id = %s", (trainer_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Trainer not found")

    return result


# ============================================================================
# OWNERS
# ============================================================================

@app.get("/owners")
async def get_owners(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    name: Optional[str] = None
):
    """Get owners"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM ra_owners WHERE 1=1"
    params = []

    if name:
        query += " AND name ILIKE %s"
        params.append(f"%{name}%")

    query += " ORDER BY name LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"count": len(results), "data": results}


# ============================================================================
# HORSES
# ============================================================================

@app.get("/horses")
async def get_horses(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    name: Optional[str] = None
):
    """Get horses"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM ra_horses WHERE 1=1"
    params = []

    if name:
        query += " AND name ILIKE %s"
        params.append(f"%{name}%")

    query += " ORDER BY name LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"count": len(results), "data": results}


@app.get("/horses/{horse_id}")
async def get_horse(horse_id: int):
    """Get specific horse by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ra_horses WHERE horse_id = %s", (horse_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Horse not found")

    return result


# ============================================================================
# RACES
# ============================================================================

@app.get("/races")
async def get_races(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    course_id: Optional[int] = None,
    race_date: Optional[date] = None
):
    """Get races"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM ra_races WHERE 1=1"
    params = []

    if course_id:
        query += " AND course_id = %s"
        params.append(course_id)

    if race_date:
        query += " AND race_date = %s"
        params.append(race_date)

    query += " ORDER BY race_date DESC, off_time DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"count": len(results), "data": results}


@app.get("/races/{race_id}")
async def get_race(race_id: str):
    """Get specific race by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ra_races WHERE race_id = %s", (race_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Race not found")

    return result


# ============================================================================
# RUNNERS
# ============================================================================

@app.get("/runners")
async def get_runners(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    race_id: Optional[str] = None,
    horse_id: Optional[int] = None
):
    """Get runners"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM ra_runners WHERE 1=1"
    params = []

    if race_id:
        query += " AND race_id = %s"
        params.append(race_id)

    if horse_id:
        query += " AND horse_id = %s"
        params.append(horse_id)

    query += " ORDER BY race_id, runner_number LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"count": len(results), "data": results}


# ============================================================================
# RESULTS
# ============================================================================

@app.get("/results")
async def get_results(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    race_date: Optional[date] = None,
    course_id: Optional[int] = None
):
    """Get race results"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM ra_results WHERE 1=1"
    params = []

    if race_date:
        query += " AND race_date = %s"
        params.append(race_date)

    if course_id:
        query += " AND course_id = %s"
        params.append(course_id)

    query += " ORDER BY race_date DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"count": len(results), "data": results}


@app.get("/results/{race_id}")
async def get_result(race_id: str):
    """Get result for specific race"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ra_results WHERE race_id = %s", (race_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    return result


# ============================================================================
# STATS
# ============================================================================

@app.get("/stats")
async def get_stats():
    """Get database statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()

    tables = [
        'ra_courses', 'ra_bookmakers', 'ra_jockeys', 'ra_trainers',
        'ra_owners', 'ra_horses', 'ra_races', 'ra_runners', 'ra_results'
    ]

    stats = {}
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        result = cursor.fetchone()
        stats[table] = result['count']

    cursor.close()
    conn.close()

    return {
        "database": "connected",
        "tables": stats,
        "total_records": sum(stats.values())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
