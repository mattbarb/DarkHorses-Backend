#!/usr/bin/env python3
"""
Root-level launcher for DarkHorses Odds API
Imports and runs the actual start.py from odds_api/
"""

import sys
import os
from pathlib import Path

if __name__ == "__main__":
    # Get the odds_api directory
    odds_api_path = Path(__file__).parent / 'odds_api'

    # Change to odds_api directory
    os.chdir(odds_api_path)

    # Add odds_api to Python path so imports work
    sys.path.insert(0, str(odds_api_path))

    # Import and run the main function
    from start import main
    main()
