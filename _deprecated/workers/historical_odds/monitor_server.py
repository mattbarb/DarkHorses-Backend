#!/usr/bin/env python3
"""
Historical Odds Monitoring Dashboard
Shows backfill progress from 2015 and daily updates
"""

from flask import Flask, render_template_string, jsonify
import threading
import logging
import json
import os
from datetime import datetime, date
from pathlib import Path

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Shared state file for IPC with parent monitor
STATS_FILE = Path('/tmp/racing_stats.json')

# Global stats storage
STATS = {
    'status': 'initializing',
    'start_time': datetime.now().isoformat(),
    'last_update': datetime.now().isoformat(),

    # Backfill progress
    'backfill_start_year': 2015,
    'backfill_current_date': None,
    'dates_processed': 0,
    'dates_remaining': 0,
    'backfill_progress_percent': 0,

    # Daily stats
    'races_processed_today': 0,
    'horses_processed_today': 0,
    'odds_stored_today': 0,
    'errors': 0,

    # Overall stats
    'total_races': 0,
    'total_odds': 0,
    'database_size_mb': 0,

    # Activity
    'current_operation': 'Initializing...',
    'recent_activity': []
}

def load_shared_stats():
    """Load stats from shared file"""
    if STATS_FILE.exists():
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load shared stats: {e}")
            return {}
    return {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Historical Odds Monitor</title>
    <meta http-equiv="refresh" content="10">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            text-align: center;
        }
        .header h1 {
            color: #f5576c;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .status-badge {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
            text-transform: uppercase;
        }
        .status-running { background: #10b981; color: white; }
        .status-backfilling { background: #3b82f6; color: white; }
        .status-waiting { background: #f59e0b; color: white; }
        .status-error { background: #ef4444; color: white; }

        /* Progress bar */
        .progress-section {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .progress-section h2 {
            color: #1e293b;
            margin-bottom: 15px;
        }
        .progress-bar-container {
            background: #e2e8f0;
            border-radius: 10px;
            height: 30px;
            overflow: hidden;
            margin: 20px 0;
        }
        .progress-bar {
            background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%);
            height: 100%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .progress-info {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-top: 15px;
        }
        .progress-info-item {
            text-align: center;
        }
        .progress-info-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #1e293b;
        }
        .progress-info-label {
            color: #64748b;
            font-size: 0.85em;
            margin-top: 5px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        .card h3 {
            color: #64748b;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }
        .card .value {
            font-size: 2.5em;
            font-weight: bold;
            color: #1e293b;
        }
        .card .subtext {
            color: #94a3b8;
            font-size: 0.85em;
            margin-top: 5px;
        }
        .activity-log {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            max-height: 400px;
            overflow-y: auto;
        }
        .activity-log h3 {
            color: #1e293b;
            margin-bottom: 15px;
        }
        .activity-item {
            padding: 10px;
            border-left: 3px solid #f5576c;
            margin-bottom: 10px;
            background: #f8fafc;
            border-radius: 5px;
        }
        .activity-time {
            color: #64748b;
            font-size: 0.8em;
        }
        .footer {
            text-align: center;
            color: white;
            margin-top: 30px;
            opacity: 0.8;
        }
        .current-op {
            background: #f8fafc;
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
            border-left: 4px solid #f5576c;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 Historical Odds Monitor</h1>
            <div class="status-badge status-{{ status_class }}">{{ status }}</div>
        </div>

        <!-- Backfill Progress -->
        <div class="progress-section">
            <h2>Backfill Progress (Since {{ backfill_start_year }})</h2>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: {{ progress_percent }}%">
                    {{ progress_percent }}%
                </div>
            </div>
            <div class="progress-info">
                <div class="progress-info-item">
                    <div class="progress-info-value">{{ dates_processed }}</div>
                    <div class="progress-info-label">Dates Completed</div>
                </div>
                <div class="progress-info-item">
                    <div class="progress-info-value">{{ dates_remaining }}</div>
                    <div class="progress-info-label">Dates Remaining</div>
                </div>
                <div class="progress-info-item">
                    <div class="progress-info-value">{{ current_date }}</div>
                    <div class="progress-info-label">Current Date</div>
                </div>
            </div>
            <div class="current-op">
                <strong>Current Operation:</strong> {{ current_operation }}
            </div>
        </div>

        <!-- Stats Grid -->
        <div class="grid">
            <div class="card">
                <h3>Today's Races</h3>
                <div class="value">{{ races_today }}</div>
                <div class="subtext">Processed today</div>
            </div>
            <div class="card">
                <h3>Today's Odds</h3>
                <div class="value">{{ odds_today }}</div>
                <div class="subtext">Records stored</div>
            </div>
            <div class="card">
                <h3>Total Races</h3>
                <div class="value">{{ total_races }}</div>
                <div class="subtext">All-time</div>
            </div>
            <div class="card">
                <h3>Total Odds</h3>
                <div class="value">{{ total_odds }}</div>
                <div class="subtext">Historical records</div>
            </div>
        </div>

        <!-- Activity Log -->
        <div class="activity-log">
            <h3>📊 Recent Activity</h3>
            {% for activity in recent_activity %}
            <div class="activity-item">
                <div class="activity-time">{{ activity.time }}</div>
                <div>{{ activity.message }}</div>
            </div>
            {% endfor %}
            {% if not recent_activity %}
            <div class="subtext">Waiting for first update...</div>
            {% endif %}
        </div>

        <div class="footer">
            🔄 Auto-refreshing every 10 seconds | Last refresh: {{ now }}<br>
            Next daily run: 1:00 AM UK time
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard"""
    status_map = {
        'initializing': 'waiting',
        'backfilling': 'backfilling',
        'running': 'running',
        'waiting': 'waiting',
        'error': 'error'
    }

    return render_template_string(
        HTML_TEMPLATE,
        status=STATS['status'],
        status_class=status_map.get(STATS['status'], 'waiting'),
        backfill_start_year=STATS['backfill_start_year'],
        progress_percent=STATS['backfill_progress_percent'],
        dates_processed=STATS['dates_processed'],
        dates_remaining=STATS['dates_remaining'],
        current_date=STATS['backfill_current_date'] or 'Not started',
        current_operation=STATS['current_operation'],
        races_today=STATS['races_processed_today'],
        odds_today=STATS['odds_stored_today'],
        total_races=STATS['total_races'],
        total_odds=STATS['total_odds'],
        recent_activity=STATS['recent_activity'][-10:],
        now=datetime.now().strftime('%H:%M:%S')
    )

@app.route('/api/stats')
def api_stats():
    """API endpoint for stats"""
    return jsonify(STATS)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'historical-odds',
        'timestamp': datetime.now().isoformat()
    })

def update_stats(**kwargs):
    """Update global stats (thread-safe) - WRITES to shared file for parent monitor"""
    try:
        # Load existing stats
        stats = load_shared_stats()
        if 'historical' not in stats:
            stats['historical'] = {
                'status': 'backfilling',
                'backfill_start_year': 2015,
                'backfill_current_date': None,
                'dates_processed': 0,
                'dates_remaining': 0,
                'backfill_progress_percent': 0,
                'races_processed_today': 0,
                'odds_stored_today': 0,
                'total_races': 0,
                'total_odds': 0,
                'current_operation': 'Starting...',
                'recent_activity': []
            }

        # Update with new values
        stats['historical'].update(kwargs)
        stats['historical']['last_update'] = datetime.now().isoformat()

        # Write back to file for parent monitor to read
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)

    except Exception as e:
        logger.error(f"Failed to update shared stats file: {e}")

    # Also update in-memory for local access
    for key, value in kwargs.items():
        if key in STATS:
            STATS[key] = value
    STATS['last_update'] = datetime.now().strftime('%H:%M:%S')

def add_activity(message):
    """Add activity to recent log - WRITES to shared file for parent monitor"""
    try:
        # Load existing stats
        stats = load_shared_stats()
        if 'historical' not in stats:
            stats['historical'] = {'recent_activity': []}
        if 'recent_activity' not in stats['historical']:
            stats['historical']['recent_activity'] = []

        # Add activity
        stats['historical']['recent_activity'].append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'message': message
        })

        # Keep last 20
        stats['historical']['recent_activity'] = stats['historical']['recent_activity'][-20:]

        # Write back
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)

    except Exception as e:
        logger.error(f"Failed to add activity to shared file: {e}")

    # Also update in-memory
    STATS['recent_activity'].append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'message': message
    })
    # Keep only last 20 items
    if len(STATS['recent_activity']) > 20:
        STATS['recent_activity'] = STATS['recent_activity'][-20:]

def start_monitor_server(port=None):
    """Start Flask server in background thread"""
    # Get port from environment variable or use default
    if port is None:
        port = int(os.getenv('PORT', '8081'))

    def run_server():
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    logger.info(f"Monitor server started on port {port}")
    add_activity("Monitor server started")
    return thread

# Make functions available for import
__all__ = ['start_monitor_server', 'update_stats', 'add_activity', 'STATS']

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Get port from environment variable or use default
    port = int(os.getenv('PORT', '8081'))
    logger.info(f"Starting monitor server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
