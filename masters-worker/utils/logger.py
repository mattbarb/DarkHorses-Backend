"""
Logging utilities for reference data fetchers
Provides consistent logging across all fetcher modules
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class FetcherLogger:
    """Custom logger for reference data fetchers"""

    def __init__(self, name: str, log_dir: Path, log_to_file: bool = True):
        """
        Initialize logger

        Args:
            name: Logger name (usually module name)
            log_dir: Directory for log files
            log_to_file: Whether to log to file in addition to console
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler
        if log_to_file:
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = log_dir / f"{name}_{timestamp}.log"

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

            self.log_file = log_file
        else:
            self.log_file = None

    def get_logger(self) -> logging.Logger:
        """Get the logger instance"""
        return self.logger

    def get_log_file_path(self) -> Optional[Path]:
        """Get path to log file"""
        return self.log_file


def get_logger(name: str, log_dir: Optional[Path] = None) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name
        log_dir: Directory for log files (default: current dir / logs)

    Returns:
        Logger instance
    """
    if log_dir is None:
        log_dir = Path(__file__).parent.parent / 'logs'

    fetcher_logger = FetcherLogger(name, log_dir)
    return fetcher_logger.get_logger()
