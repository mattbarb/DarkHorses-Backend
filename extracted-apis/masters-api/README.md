# Racing Masters API

FastAPI web service providing REST API access to UK & Ireland horse racing reference data.

## Features

- **18 REST Endpoints**: Complete racing reference data API
- **Comprehensive Data**: Courses, bookmakers, jockeys, trainers, owners, horses, races, results
- **Swagger Docs**: API documentation at `/docs`
- **PostgreSQL Direct**: High-performance direct database queries

## Endpoints

### Core
- `GET /` - API information
- `GET /health` - Health check
- `GET /stats` - Database statistics

### Reference Data
- `GET /courses` - Racing venues (filter by region, name)
- `GET /courses/{id}` - Specific course details
- `GET /bookmakers` - Betting companies
- `GET /jockeys` - Jockey profiles (filter by name)
- `GET /jockeys/{id}` - Specific jockey
- `GET /trainers` - Trainer profiles
- `GET /trainers/{id}` - Specific trainer
- `GET /owners` - Horse owners
- `GET /horses` - Horse profiles
- `GET /horses/{id}` - Specific horse with pedigree

### Race Data
- `GET /races` - Race cards (filter by date, course)
- `GET /races/{id}` - Specific race details
- `GET /runners` - Race entries (filter by race, horse)
- `GET /results` - Race results (filter by date, course)
- `GET /results/{id}` - Result for specific race

## Configuration

Copy `.env.example` to `.env` and configure:
- `DATABASE_URL` - PostgreSQL connection string

## Running Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Visit: http://localhost:8001/docs

## Deploy to Render.com

```bash
# Using render.yaml in this directory
render deploy
```

Service Type: Web Service
Cost: $7/month (Starter) or Free tier

## Database Tables

Reads from:
- `ra_courses` - Racing venues
- `ra_bookmakers` - Bookmakers
- `ra_jockeys` - Jockey profiles
- `ra_trainers` - Trainer profiles
- `ra_owners` - Owner profiles
- `ra_horses` - Horse profiles
- `ra_horse_pedigree` - Breeding data
- `ra_races` - Race cards
- `ra_runners` - Race entries
- `ra_results` - Race outcomes

## Data Coverage

- **Regions**: UK (GB) and Ireland (IRE) only
- **Time Period**: 2015 to present
- **Updates**: Daily (races/results), Weekly (people/horses), Monthly (static data)
