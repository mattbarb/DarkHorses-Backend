# Quick Start Guide - DarkHorses-Odds-Workers

## Overview

Betting odds collection worker

## Prerequisites

- Python 3.9+
- PostgreSQL (if database required)
- Redis (if caching/queues required)
- Environment variables configured

## Installation

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/DarkHorses-Odds-Workers.git
cd DarkHorses-Odds-Workers
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Set up environment:**

```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run the application:**

```bash
# Development
python main.py

# Or with uvicorn (for API)
uvicorn main:app --reload
```

## Configuration

Key environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/dbname

# API Keys (if needed)
API_KEY=your_api_key_here

# Redis (if needed)
REDIS_URL=redis://localhost:6379
```

## Basic Usage

### Example 1: [Common Task]

```bash
# Command or code example
```

### Example 2: [Another Task]

```bash
# Command or code example
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov
```

## Troubleshooting

### Common Issues

**Issue 1: Connection Error**
- Check database is running
- Verify connection string in .env

**Issue 2: Import Error**
- Ensure all dependencies installed
- Check Python version (3.9+)

## Next Steps

- Read [Architecture Documentation](ARCHITECTURE.md)
- Review [API Reference](API_REFERENCE.md) (if applicable)
- Check [Contributing Guidelines](../CONTRIBUTING.md)

## Links

- Main documentation: [Notion Workspace](https://notion.so/2850795b42db80cbbe49eda4b40f7bbb)
- GitHub: https://github.com/yourusername/DarkHorses-Odds-Workers
- Issues: https://github.com/yourusername/DarkHorses-Odds-Workers/issues
