#!/bin/bash

# Installation script for Odds Statistics Tracker

echo "=========================================="
echo "  Odds Statistics Tracker - Installation"
echo "=========================================="
echo ""

# Navigate to script directory
cd "$(dirname "$0")"

# Check Python version
echo "Checking Python version..."
python3 --version

# Create virtual environment (optional)
read -p "Create virtual environment? (y/N): " create_venv
if [[ $create_venv == "y" || $create_venv == "Y" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ Virtual environment created and activated"
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Test installation
echo ""
echo "Testing installation..."
python3 -c "import psycopg2; import tabulate; import colorama; print('✅ All dependencies installed successfully')"

# Test database connection
echo ""
echo "Testing database connection..."
python3 -c "from database import DatabaseConnection; from config import Config; db = DatabaseConnection(Config.DATABASE_URL); result = db.test_connection(); exit(0 if result else 1)"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "  ✅ Installation Complete!"
    echo "=========================================="
    echo ""
    echo "Run statistics tracker:"
    echo "  python3 stats_tracker.py"
    echo ""
    echo "See README.md for more usage examples"
else
    echo ""
    echo "⚠️  Database connection test failed"
    echo "Check your DATABASE_URL in .env file"
fi
