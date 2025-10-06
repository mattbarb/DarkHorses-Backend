#!/usr/bin/env python3
"""
Live Odds Monitoring Dashboard
Simple web interface showing real-time progress and statistics
"""

from flask import Flask, render_template_string, jsonify
import threading
import logging
import json
from datetime import datetime
from pathlib import Path
import os

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Shared state file for IPC with parent monitor
STATS_FILE = Path('/tmp/racing_stats.json')

# Global stats storage
STATS = {
    'status': 'initializing',
    'start_time': datetime.now().isoformat(),
    'last_update': datetime.now().isoformat(),
    'races_processed': 0,
    'horses_processed': 0,
    'odds_stored': 0,
    'errors': 0,
    'current_race': None,
    'upcoming_races': 0,
    'bookmakers_active': [],
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
    <title>Live Odds Monitor</title>
    <meta http-equiv="refresh" content="5">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            color: #667eea;
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
        .status-initializing { background: #f59e0b; color: white; }
        .status-error { background: #ef4444; color: white; }

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
            border-left: 3px solid #667eea;
            margin-bottom: 10px;
            background: #f8fafc;
            border-radius: 5px;
        }
        .activity-time {
            color: #64748b;
            font-size: 0.8em;
        }
        .bookmaker-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        .bookmaker-tag {
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.8em;
        }
        .footer {
            text-align: center;
            color: white;
            margin-top: 30px;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏇 Live Odds Monitor</h1>
            <div class="status-badge status-{{ status_class }}">{{ status }}</div>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Races Processed</h3>
                <div class="value">{{ races_processed }}</div>
                <div class="subtext">Today's races</div>
            </div>
            <div class="card">
                <h3>Horses Tracked</h3>
                <div class="value">{{ horses_processed }}</div>
                <div class="subtext">Active runners</div>
            </div>
            <div class="card">
                <h3>Odds Captured</h3>
                <div class="value">{{ odds_stored }}</div>
                <div class="subtext">Total odds records</div>
            </div>
            <div class="card">
                <h3>Errors</h3>
                <div class="value" style="color: {% if errors > 0 %}#ef4444{% else %}#10b981{% endif %}">{{ errors }}</div>
                <div class="subtext">{{ error_text }}</div>
            </div>
        </div>

        <div class="grid" style="grid-template-columns: 1fr 1fr;">
            <div class="card">
                <h3>Current Status</h3>
                <div class="subtext" style="font-size: 1em; margin-top: 15px;">
                    <strong>Upcoming Races:</strong> {{ upcoming_races }}<br>
                    <strong>Current Race:</strong> {{ current_race or 'Waiting...' }}<br>
                    <strong>Last Update:</strong> {{ last_update }}<br>
                    <strong>Uptime:</strong> {{ uptime }}
                </div>

                {% if bookmakers_active %}
                <h3 style="margin-top: 20px;">Active Bookmakers</h3>
                <div class="bookmaker-tags">
                    {% for bookie in bookmakers_active %}
                    <div class="bookmaker-tag">{{ bookie }}</div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>

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
        </div>

        <div class="footer">
            🔄 Auto-refreshing every 5 seconds | Last refresh: {{ now }}
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard"""
    status_map = {
        'initializing': 'initializing',
        'running': 'running',
        'error': 'error'
    }

    start_time = datetime.fromisoformat(STATS['start_time'])
    uptime_seconds = (datetime.now() - start_time).total_seconds()
    uptime_str = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"

    return render_template_string(
        HTML_TEMPLATE,
        status=STATS['status'],
        status_class=status_map.get(STATS['status'], 'initializing'),
        races_processed=STATS['races_processed'],
        horses_processed=STATS['horses_processed'],
        odds_stored=STATS['odds_stored'],
        errors=STATS['errors'],
        error_text='All good!' if STATS['errors'] == 0 else 'Check logs',
        upcoming_races=STATS['upcoming_races'],
        current_race=STATS['current_race'],
        last_update=STATS['last_update'],
        uptime=uptime_str,
        bookmakers_active=STATS['bookmakers_active'][:10],  # Show top 10
        recent_activity=STATS['recent_activity'][-10:],  # Last 10 items
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
        'service': 'live-odds',
        'timestamp': datetime.now().isoformat()
    })

def update_stats(**kwargs):
    """Update global stats (thread-safe) - WRITES to shared file for parent monitor"""
    try:
        # Load existing stats
        stats = load_shared_stats()
        if 'live' not in stats:
            stats['live'] = {
                'status': 'running',
                'races_processed': 0,
                'horses_processed': 0,
                'odds_stored': 0,
                'errors': 0,
                'current_race': None,
                'bookmakers_active': [],
                'recent_activity': []
            }

        # Update with new values
        stats['live'].update(kwargs)
        stats['live']['last_update'] = datetime.now().isoformat()

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
        if 'live' not in stats:
            stats['live'] = {'recent_activity': []}
        if 'recent_activity' not in stats['live']:
            stats['live']['recent_activity'] = []

        # Add activity
        stats['live']['recent_activity'].append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'message': message
        })

        # Keep last 20
        stats['live']['recent_activity'] = stats['live']['recent_activity'][-20:]

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
        port = int(os.getenv('PORT', '8080'))

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
    port = int(os.getenv('PORT', '8080'))
    logger.info(f"Starting monitor server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
