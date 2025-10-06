"""
Console/terminal formatter for statistics
"""
from typing import Dict, List
from tabulate import tabulate


class ConsoleFormatter:
    """Format statistics for console/terminal display"""

    def format_stats(self, stats: Dict) -> str:
        """Format all statistics for console output"""
        output = []

        # Header
        output.append("=" * 80)
        output.append("  ODDS DATA PIPELINE STATISTICS REPORT")
        output.append("=" * 80)
        output.append(f"  Timestamp: {stats.get('timestamp', 'N/A')}")
        output.append("=" * 80)
        output.append("")

        # Historical odds stats
        if 'ra_odds_historical' in stats:
            output.append(self._format_historical_stats(stats['ra_odds_historical']))

        # Live odds stats
        if 'ra_odds_live' in stats:
            output.append(self._format_live_stats(stats['ra_odds_live']))

        # Footer
        output.append("=" * 80)
        output.append("  END OF REPORT")
        output.append("=" * 80)

        return "\n".join(output)

    def _format_historical_stats(self, stats: Dict) -> str:
        """Format historical odds statistics"""
        output = []

        output.append("┌" + "─" * 78 + "┐")
        output.append("│ TABLE: ra_odds_historical" + " " * 52 + "│")
        output.append("└" + "─" * 78 + "┘")
        output.append("")

        # Basic metrics
        if 'basic_metrics' in stats:
            output.append("📊 BASIC METRICS")
            metrics = stats['basic_metrics']
            data = [
                ["Total Records", f"{metrics.get('total_records', 0):,}"],
                ["Earliest Race Date", metrics.get('earliest_race_date', 'N/A')],
                ["Latest Race Date", metrics.get('latest_race_date', 'N/A')],
                ["Date Range (days)", metrics.get('date_range_days', 'N/A')],
                ["Latest Update", metrics.get('latest_update', 'N/A')]
            ]
            output.append(tabulate(data, headers=["Metric", "Value"], tablefmt="simple"))
            output.append("")

        # Recent activity
        if 'recent_activity' in stats:
            output.append("📈 RECENT ACTIVITY")
            activity = stats['recent_activity']
            data = [
                ["Last Hour", f"{activity.get('records_last_hour', 0):,}"],
                ["Last 24 Hours", f"{activity.get('records_last_24h', 0):,}"],
                ["Last 7 Days", f"{activity.get('records_last_7d', 0):,}"]
            ]
            output.append(tabulate(data, headers=["Period", "Records Added"], tablefmt="simple"))
            output.append("")

        # Unique entities
        if 'unique_entities' in stats:
            output.append("🔢 UNIQUE ENTITIES")
            entities = stats['unique_entities']
            data = [
                ["Horses", f"{entities.get('unique_horses', 0):,}"],
                ["Tracks", f"{entities.get('unique_tracks', 0):,}"],
                ["Jockeys", f"{entities.get('unique_jockeys', 0):,}"],
                ["Trainers", f"{entities.get('unique_trainers', 0):,}"],
                ["Countries", f"{entities.get('unique_countries', 0):,}"]
            ]
            output.append(tabulate(data, headers=["Entity", "Count"], tablefmt="simple"))
            output.append("")

        # Records per date
        if 'records_per_date' in stats and stats['records_per_date']:
            output.append("📅 RECORDS PER DATE (Last 7 Days)")
            data = [[row['race_date'], f"{row['record_count']:,}"] for row in stats['records_per_date']]
            output.append(tabulate(data, headers=["Date", "Records"], tablefmt="simple"))
            output.append("")

        # Country distribution
        if 'country_distribution' in stats and stats['country_distribution']:
            output.append("🌍 COUNTRY DISTRIBUTION")
            data = [[row['country'], f"{row['record_count']:,}", f"{row['percentage']:.2f}%"]
                    for row in stats['country_distribution'][:10]]
            output.append(tabulate(data, headers=["Country", "Records", "%"], tablefmt="simple"))
            output.append("")

        # Track distribution
        if 'track_distribution' in stats and stats['track_distribution']:
            output.append("🏇 TOP 10 TRACKS")
            data = [[row['track'], f"{row['record_count']:,}"] for row in stats['track_distribution'][:10]]
            output.append(tabulate(data, headers=["Track", "Records"], tablefmt="simple"))
            output.append("")

        # Data quality
        if 'data_quality' in stats:
            output.append("✅ DATA QUALITY")
            quality = stats['data_quality']
            total = quality.get('total_records', 1)
            data = [
                ["date_of_race", quality.get('null_date_of_race', 0),
                 f"{100 - (quality.get('null_date_of_race', 0) / total * 100):.2f}%"],
                ["track", quality.get('null_track', 0),
                 f"{100 - (quality.get('null_track', 0) / total * 100):.2f}%"],
                ["horse_name", quality.get('null_horse_name', 0),
                 f"{100 - (quality.get('null_horse_name', 0) / total * 100):.2f}%"],
                ["industry_sp", quality.get('null_industry_sp', 0),
                 f"{100 - (quality.get('null_industry_sp', 0) / total * 100):.2f}%"]
            ]
            output.append(tabulate(data, headers=["Field", "NULL Count", "Complete %"], tablefmt="simple"))
            output.append("")

        return "\n".join(output)

    def _format_live_stats(self, stats: Dict) -> str:
        """Format live odds statistics"""
        output = []

        output.append("┌" + "─" * 78 + "┐")
        output.append("│ TABLE: ra_odds_live" + " " * 58 + "│")
        output.append("└" + "─" * 78 + "┘")
        output.append("")

        # Basic metrics
        if 'basic_metrics' in stats:
            output.append("📊 BASIC METRICS")
            metrics = stats['basic_metrics']
            data = [
                ["Total Records", f"{metrics.get('total_records', 0):,}"],
                ["Earliest Race Date", metrics.get('earliest_race_date', 'N/A')],
                ["Latest Race Date", metrics.get('latest_race_date', 'N/A')],
                ["Latest Odds Timestamp", metrics.get('latest_odds_timestamp', 'N/A')],
                ["Latest Fetch", metrics.get('latest_fetch', 'N/A')]
            ]
            output.append(tabulate(data, headers=["Metric", "Value"], tablefmt="simple"))
            output.append("")

        # Recent activity
        if 'recent_activity' in stats:
            output.append("📈 RECENT ACTIVITY")
            activity = stats['recent_activity']
            data = [
                ["Last Hour", f"{activity.get('records_last_hour', 0):,}"],
                ["Last 24 Hours", f"{activity.get('records_last_24h', 0):,}"]
            ]
            output.append(tabulate(data, headers=["Period", "Records Fetched"], tablefmt="simple"))
            output.append("")

        # Unique entities
        if 'unique_entities' in stats:
            output.append("🔢 UNIQUE ENTITIES")
            entities = stats['unique_entities']
            data = [
                ["Races", f"{entities.get('unique_races', 0):,}"],
                ["Horses", f"{entities.get('unique_horses', 0):,}"],
                ["Courses", f"{entities.get('unique_courses', 0):,}"],
                ["Bookmakers", f"{entities.get('unique_bookmakers', 0):,}"]
            ]
            output.append(tabulate(data, headers=["Entity", "Count"], tablefmt="simple"))
            output.append("")

        # Bookmaker coverage
        if 'bookmaker_coverage' in stats and stats['bookmaker_coverage']:
            output.append("📚 BOOKMAKER COVERAGE")
            data = [[row['bookmaker_name'], row['bookmaker_type'], f"{row['odds_count']:,}",
                     row['races_covered'], str(row['latest_odds'])[:19]]
                    for row in stats['bookmaker_coverage'][:10]]
            output.append(tabulate(data, headers=["Bookmaker", "Type", "Odds", "Races", "Latest"], tablefmt="simple"))
            output.append("")

        # Records per date
        if 'records_per_date' in stats and stats['records_per_date']:
            output.append("📅 RECORDS PER DATE (Last 7 Days)")
            data = [[str(row['race_date']), f"{row['record_count']:,}", row['unique_races'], row['unique_bookmakers']]
                    for row in stats['records_per_date']]
            output.append(tabulate(data, headers=["Date", "Records", "Races", "Bookmakers"], tablefmt="simple"))
            output.append("")

        # Data quality
        if 'data_quality' in stats:
            output.append("✅ DATA QUALITY")
            quality = stats['data_quality']
            total = quality.get('total_records', 1)
            data = [
                ["race_id", quality.get('null_race_id', 0),
                 f"{100 - (quality.get('null_race_id', 0) / total * 100):.2f}%"],
                ["horse_id", quality.get('null_horse_id', 0),
                 f"{100 - (quality.get('null_horse_id', 0) / total * 100):.2f}%"],
                ["bookmaker_id", quality.get('null_bookmaker_id', 0),
                 f"{100 - (quality.get('null_bookmaker_id', 0) / total * 100):.2f}%"],
                ["odds_decimal", quality.get('null_odds_decimal', 0),
                 f"{100 - (quality.get('null_odds_decimal', 0) / total * 100):.2f}%"]
            ]
            output.append(tabulate(data, headers=["Field", "NULL Count", "Complete %"], tablefmt="simple"))
            output.append("")

        # Market status
        if 'market_status' in stats and stats['market_status']:
            output.append("📊 MARKET STATUS")
            data = [[row['market_status'], f"{row['record_count']:,}", f"{row['percentage']:.2f}%"]
                    for row in stats['market_status']]
            output.append(tabulate(data, headers=["Status", "Records", "%"], tablefmt="simple"))
            output.append("")

        return "\n".join(output)
