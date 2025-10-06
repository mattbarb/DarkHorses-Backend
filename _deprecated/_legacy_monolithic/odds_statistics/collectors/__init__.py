"""
Statistics collectors for odds data pipeline
"""
from .historical_collector import HistoricalOddsCollector
from .live_collector import LiveOddsCollector

__all__ = ['HistoricalOddsCollector', 'LiveOddsCollector']
