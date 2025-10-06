"""
Health Monitoring Module
Provides health check and metrics for production monitoring
"""

import os
import psutil
from datetime import datetime, timedelta
from typing import Dict, Optional


class HealthMonitor:
    """Monitor and report service health status"""

    def __init__(self):
        """Initialize health monitor"""
        self.start_time = datetime.now()
        self.last_fetch_time = None
        self.last_fetch_success = None
        self.total_fetches = 0
        self.successful_fetches = 0
        self.failed_fetches = 0
        self.status = 'starting'
        self.status_message = 'Service initializing'
        self.metrics_data = {}

    def update_status(self, status: str, message: str = '') -> None:
        """Update service health status"""
        self.status = status
        self.status_message = message
        self.metrics_data['last_status_update'] = datetime.now().isoformat()

    def record_fetch(self, success: bool, records: int = 0) -> None:
        """Record a fetch operation"""
        self.last_fetch_time = datetime.now()
        self.last_fetch_success = success
        self.total_fetches += 1

        if success:
            self.successful_fetches += 1
            self.metrics_data['last_successful_fetch'] = self.last_fetch_time.isoformat()
            self.metrics_data['last_fetch_records'] = records
        else:
            self.failed_fetches += 1
            self.metrics_data['last_failed_fetch'] = self.last_fetch_time.isoformat()

    def get_status(self) -> Dict:
        """Get current health status"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        # Determine overall health
        if self.status in ['healthy', 'starting']:
            http_status = 200
        elif self.status == 'degraded':
            http_status = 200
        else:
            http_status = 503

        return {
            'status': self.status,
            'message': self.status_message,
            'uptime_seconds': int(uptime),
            'last_fetch': self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            'last_fetch_success': self.last_fetch_success,
            'http_status': http_status
        }

    def get_metrics(self) -> Dict:
        """Get detailed metrics"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        # Get system metrics
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent(interval=1)
        except:
            memory_info = None
            cpu_percent = 0

        metrics = {
            'service': {
                'uptime_seconds': int(uptime),
                'start_time': self.start_time.isoformat(),
                'status': self.status,
                'version': os.getenv('APP_VERSION', '1.0.0')
            },
            'fetches': {
                'total': self.total_fetches,
                'successful': self.successful_fetches,
                'failed': self.failed_fetches,
                'success_rate': (self.successful_fetches / self.total_fetches * 100) if self.total_fetches > 0 else 0,
                'last_fetch_time': self.last_fetch_time.isoformat() if self.last_fetch_time else None,
                'last_fetch_success': self.last_fetch_success
            },
            'system': {
                'memory_mb': memory_info.rss / 1024 / 1024 if memory_info else 0,
                'cpu_percent': cpu_percent,
                'python_version': os.sys.version
            },
            'environment': {
                'fetch_days_back': os.getenv('FETCH_DAYS_BACK', '7'),
                'fetch_days_forward': os.getenv('FETCH_DAYS_FORWARD', '2'),
                'max_workers': os.getenv('MAX_WORKERS', '3'),
                'batch_size': os.getenv('BATCH_SIZE', '100')
            },
            **self.metrics_data
        }

        return metrics

    def check_health_conditions(self) -> None:
        """Check various health conditions and update status accordingly"""

        # Check if last fetch was too long ago
        if self.last_fetch_time:
            hours_since_fetch = (datetime.now() - self.last_fetch_time).total_seconds() / 3600
            max_hours = int(os.getenv('HEALTH_MAX_HOURS_SINCE_FETCH', '8'))

            if hours_since_fetch > max_hours:
                self.update_status('degraded', f'No fetch for {hours_since_fetch:.1f} hours')

        # Check failure rate
        if self.total_fetches > 10:
            failure_rate = self.failed_fetches / self.total_fetches
            if failure_rate > 0.5:
                self.update_status('unhealthy', f'High failure rate: {failure_rate:.1%}')