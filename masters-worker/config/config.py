"""
Configuration Management for Racing API Reference Data Fetcher
Handles credentials, paths, and fetcher settings
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


@dataclass
class APIConfig:
    """Racing API configuration"""
    base_url: str = "https://api.theracingapi.com/v1"
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    max_retries: int = 5
    retry_delay: float = 2.0
    rate_limit_per_second: int = 2


@dataclass
class SupabaseConfig:
    """Supabase database configuration"""
    url: Optional[str] = None
    service_key: Optional[str] = None
    batch_size: int = 100
    max_retries: int = 3


@dataclass
class PathConfig:
    """Path configuration"""
    base_dir: Path
    logs_dir: Path
    config_dir: Path

    def __post_init__(self):
        # Create directories if they don't exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)


class ReferenceDataConfig:
    """Main configuration class for reference data fetching"""

    def __init__(self, env_file: Optional[str] = None):
        """Initialize configuration"""
        # Load environment variables
        if env_file:
            load_dotenv(env_file)
        else:
            # Search for .env.local in parent directories
            search_paths = [
                Path(__file__).parent.parent / '.env.local',
                Path(__file__).parent.parent.parent / '.env.local',
            ]
            for path in search_paths:
                if path.exists():
                    load_dotenv(path)
                    break

        # Initialize path configuration
        self.paths = PathConfig(
            base_dir=Path(__file__).parent.parent,
            logs_dir=Path(__file__).parent.parent / 'logs',
            config_dir=Path(__file__).parent
        )

        # Initialize API configuration
        self.api = APIConfig(
            username=os.getenv('RACING_API_USERNAME'),
            password=os.getenv('RACING_API_PASSWORD'),
            base_url=os.getenv('RACING_API_BASE_URL', 'https://api.theracingapi.com/v1'),
            timeout=int(os.getenv('RACING_API_TIMEOUT', '30')),
            max_retries=int(os.getenv('RACING_API_MAX_RETRIES', '5'))
        )

        # Initialize Supabase configuration
        self.supabase = SupabaseConfig(
            url=os.getenv('SUPABASE_URL'),
            service_key=os.getenv('SUPABASE_SERVICE_KEY'),
            batch_size=int(os.getenv('SUPABASE_BATCH_SIZE', '100'))
        )

        # Validate configuration
        self._validate()

    def _validate(self):
        """Validate required configuration"""
        errors = []

        # Check API credentials
        if not self.api.username:
            errors.append("Missing RACING_API_USERNAME")
        if not self.api.password:
            errors.append("Missing RACING_API_PASSWORD")

        # Check Supabase credentials
        if not self.supabase.url:
            errors.append("Missing SUPABASE_URL")
        if not self.supabase.service_key:
            errors.append("Missing SUPABASE_SERVICE_KEY")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

    def get_log_file(self, log_name: str) -> Path:
        """Get path to log file"""
        return self.paths.logs_dir / f"{log_name}.log"


# Global configuration instance
_config = None


def get_config() -> ReferenceDataConfig:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = ReferenceDataConfig()
    return _config
