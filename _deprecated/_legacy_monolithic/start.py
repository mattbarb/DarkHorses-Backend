#!/usr/bin/env python3
"""
DarkHorses All-in-One Startup Script
Runs API server and background scheduler in a single process
"""

import sys
import os
import threading
import signal
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = threading.Event()


def run_scheduler():
    """Run the consolidated scheduler in background thread"""
    logger.info("📍 Scheduler thread started, attempting import...")
    try:
        from scheduler import ConsolidatedScheduler
        logger.info("📍 Scheduler imported successfully")

        logger.info("🚀 Starting background scheduler...")
        scheduler = ConsolidatedScheduler()
        logger.info("📍 Scheduler instance created")

        scheduler.run()
    except Exception as e:
        logger.error(f"❌ Scheduler failed to start: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        shutdown_flag.set()


def run_api():
    """Run the FastAPI server"""
    try:
        import uvicorn
        from main import app

        logger.info("🚀 Starting API server...")

        # Get port from environment or use default
        port = int(os.getenv('PORT', 8000))
        host = os.getenv('HOST', '0.0.0.0')

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"❌ API server failed to start: {e}")
        shutdown_flag.set()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("🛑 Shutdown signal received, stopping services...")
    shutdown_flag.set()


def main():
    """Main entry point - starts all services"""

    # Create logs directory
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    logger.info("=" * 60)
    logger.info("🏇 DarkHorses Racing Odds System")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Starting all services:")
    logger.info("  1. Background Scheduler (live odds, historical odds, statistics)")
    logger.info("  2. FastAPI Server (API + Dashboard UI)")
    logger.info("")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    # Run API in main thread
    try:
        run_api()
    except KeyboardInterrupt:
        logger.info("🛑 Keyboard interrupt received")
    finally:
        shutdown_flag.set()
        logger.info("✅ All services stopped")


if __name__ == "__main__":
    main()
