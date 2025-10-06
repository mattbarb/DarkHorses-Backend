#!/usr/bin/env python3
"""
DarkHorses Background Workers - Consolidated Entry Point
Runs all data collection schedulers in a single process
"""

import sys
import os
import signal
from pathlib import Path
import logging

# Add worker directories to Python path
sys.path.insert(0, str(Path(__file__).parent / 'live-odds-worker'))
sys.path.insert(0, str(Path(__file__).parent / 'historical-odds-worker'))
sys.path.insert(0, str(Path(__file__).parent / 'statistics-worker'))

# Configure logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'workers.log'),
        logging.StreamHandler()
    ]
)

# Reduce noise from third-party libraries
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    logger.info("🛑 Shutdown signal received, stopping workers...")
    running = False


def main():
    """Main entry point - starts all background workers"""

    logger.info("=" * 60)
    logger.info("🏇 DarkHorses Background Workers - Consolidated Service")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Starting data collection services:")
    logger.info("  1. Live Odds Scheduler (adaptive intervals)")
    logger.info("  2. Historical Odds Scheduler (daily at 1:00 AM)")
    logger.info("  3. Statistics Updater (every 10 minutes)")
    logger.info("")
    logger.info("⚠️  Running as ONE consolidated service")
    logger.info("")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Import and run consolidated scheduler
    try:
        from scheduler import ConsolidatedScheduler

        logger.info("🚀 Starting consolidated scheduler...")
        scheduler = ConsolidatedScheduler()
        scheduler.run()

    except KeyboardInterrupt:
        logger.info("🛑 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Workers failed to start: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    finally:
        logger.info("✅ Workers stopped")


if __name__ == "__main__":
    main()
