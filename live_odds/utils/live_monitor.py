"""
Live Odds Monitoring Module
Real-time monitoring and alerting for live odds service
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class LiveOddsMonitor:
    """Monitor live odds service health and performance"""

    def __init__(self):
        """Initialize monitor"""
        self.start_time = datetime.now()
        self.last_update_time = None
        self.last_update_success = None
        self.total_updates = 0
        self.successful_updates = 0
        self.failed_updates = 0
        self.total_records = 0
        self.total_bookmakers = set()
        self.total_races = 0
        self.status = 'starting'
        self.status_message = 'Service initializing'
        self.recent_errors = []
        self.performance_metrics = []

    def update_status(self, status: str, message: str = ''):
        """Update service status"""
        self.status = status
        self.status_message = message

    def record_update(self, success: bool, records: int = 0, bookmakers: int = 0,
                     races: int = 0, error: str = None):
        """Record an update cycle"""
        self.last_update_time = datetime.now()
        self.last_update_success = success
        self.total_updates += 1

        if success:
            self.successful_updates += 1
            self.total_records += records
            self.total_races += races
            if bookmakers > 0:
                for i in range(bookmakers):
                    self.total_bookmakers.add(f"bookmaker_{i}")
            self.status = 'healthy'
            self.status_message = f"Last update: {records} records from {bookmakers} bookmakers"

            # Track performance
            if len(self.performance_metrics) > 100:
                self.performance_metrics.pop(0)
            self.performance_metrics.append({
                'timestamp': self.last_update_time,
                'records': records,
                'bookmakers': bookmakers,
                'races': races
            })
        else:
            self.failed_updates += 1
            self.status = 'degraded' if self.successful_updates > 0 else 'unhealthy'
            self.status_message = f"Update failed: {error or 'Unknown error'}"

            # Track errors
            if error:
                if len(self.recent_errors) > 10:
                    self.recent_errors.pop(0)
                self.recent_errors.append({
                    'timestamp': self.last_update_time,
                    'error': error
                })

    def get_status(self) -> Dict:
        """Get current health status"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        # Check staleness
        if self.last_update_time:
            minutes_since_update = (datetime.now() - self.last_update_time).total_seconds() / 60
            if minutes_since_update > 10:
                self.status = 'stale'
                self.status_message = f"No updates for {minutes_since_update:.0f} minutes"

        return {
            'status': self.status,
            'message': self.status_message,
            'uptime_seconds': int(uptime),
            'last_update': self.last_update_time.isoformat() if self.last_update_time else None,
            'last_update_success': self.last_update_success,
            'total_updates': self.total_updates,
            'success_rate': (self.successful_updates / self.total_updates * 100) if self.total_updates > 0 else 0
        }

    def get_metrics(self) -> Dict:
        """Get detailed metrics"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        # Calculate averages
        avg_records = 0
        avg_bookmakers = 0
        if self.performance_metrics:
            avg_records = sum(m['records'] for m in self.performance_metrics) / len(self.performance_metrics)
            avg_bookmakers = sum(m['bookmakers'] for m in self.performance_metrics) / len(self.performance_metrics)

        return {
            'service': {
                'status': self.status,
                'uptime_seconds': int(uptime),
                'start_time': self.start_time.isoformat()
            },
            'updates': {
                'total': self.total_updates,
                'successful': self.successful_updates,
                'failed': self.failed_updates,
                'success_rate': (self.successful_updates / self.total_updates * 100) if self.total_updates > 0 else 0,
                'last_update': self.last_update_time.isoformat() if self.last_update_time else None
            },
            'data': {
                'total_records': self.total_records,
                'total_races': self.total_races,
                'unique_bookmakers': len(self.total_bookmakers),
                'avg_records_per_update': avg_records,
                'avg_bookmakers_per_update': avg_bookmakers
            },
            'performance': {
                'recent_updates': self.performance_metrics[-10:],
                'updates_per_hour': self.total_updates / (uptime / 3600) if uptime > 0 else 0
            },
            'errors': {
                'recent': self.recent_errors,
                'total_failures': self.failed_updates
            },
            'configuration': {
                'update_interval': os.getenv('LIVE_UPDATE_INTERVAL', '60'),
                'race_window_hours': os.getenv('LIVE_RACE_WINDOW', '4'),
                'max_workers': os.getenv('LIVE_MAX_WORKERS', '5')
            }
        }

    def get_alerts(self) -> List[Dict]:
        """Get any active alerts"""
        alerts = []

        # Check for high failure rate
        if self.total_updates > 10:
            failure_rate = self.failed_updates / self.total_updates
            if failure_rate > 0.3:
                alerts.append({
                    'level': 'critical' if failure_rate > 0.5 else 'warning',
                    'message': f'High failure rate: {failure_rate:.1%}',
                    'timestamp': datetime.now().isoformat()
                })

        # Check for staleness
        if self.last_update_time:
            minutes_since = (datetime.now() - self.last_update_time).total_seconds() / 60
            if minutes_since > 10:
                alerts.append({
                    'level': 'warning' if minutes_since < 30 else 'critical',
                    'message': f'No updates for {minutes_since:.0f} minutes',
                    'timestamp': datetime.now().isoformat()
                })

        # Check for low bookmaker coverage
        if self.total_updates > 5 and len(self.total_bookmakers) < 5:
            alerts.append({
                'level': 'warning',
                'message': f'Low bookmaker coverage: only {len(self.total_bookmakers)} bookmakers',
                'timestamp': datetime.now().isoformat()
            })

        return alerts