"""
JSON formatter for statistics
"""
import json
from typing import Dict
from datetime import datetime, date
from decimal import Decimal


class JSONFormatter:
    """Format statistics as JSON"""

    def format_stats(self, stats: Dict) -> str:
        """Format all statistics as JSON"""
        return json.dumps(stats, indent=2, default=self._json_serial)

    def _json_serial(self, obj):
        """JSON serializer for objects not serializable by default"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Type {type(obj)} not serializable")
