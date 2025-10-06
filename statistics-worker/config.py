"""
Configuration management for odds statistics tracker
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent / '.env.local'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try .env if .env.local doesn't exist
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

class Config:
    """Configuration settings"""

    # Database connection - Direct PostgreSQL for read-only statistics queries
    # (Supabase client doesn't support complex aggregation queries needed for statistics)
    # Main data pipeline uses Supabase client for write operations
    #
    # IMPORTANT: Use connection pooler URL (not direct database URL)
    # Render.com doesn't support IPv6, and direct db.*.supabase.co is IPv6-only
    # Use SESSION_POOLER or TRANSACTION_POOLER with pooler.supabase.com hostname
    DATABASE_URL = os.getenv('SESSION_POOLER') or os.getenv('TRANSACTION_POOLER') or os.getenv('DATABASE_URL')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = str(Path(__file__).parent / 'logs' / 'stats_tracker.log')

    # Query defaults
    DEFAULT_DAYS_LOOKBACK = 7
    DEFAULT_TOP_N_TRACKS = 20
    DEFAULT_TOP_N_COUNTRIES = 10

    # Output
    DEFAULT_OUTPUT_FORMAT = 'console'  # console, json, csv
    DEFAULT_OUTPUT_DIR = str(Path(__file__).parent / 'output')

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL must be set in environment")
        return True
