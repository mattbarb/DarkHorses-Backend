"""
Database connection manager for PostgreSQL (read-only statistics queries)

Note: This module uses direct PostgreSQL connection for complex aggregation queries.
The main data pipeline (live_odds, historical_odds) uses Supabase client for write operations.
"""
import logging
import socket
import re
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger('STATISTICS_DB')


class DatabaseConnection:
    """Manages PostgreSQL database connections for read-only statistics queries"""

    def __init__(self, connection_string: str):
        self.connection_string = self._force_ipv4_connection(connection_string)
        self.connection = None

    def _force_ipv4_connection(self, connection_string: str) -> str:
        """
        Force IPv4 connection by resolving hostname to IPv4 address.
        This fixes the Render.com IPv6 issue.
        """
        try:
            # Extract hostname from connection string
            # Format: postgresql://user:pass@hostname:port/database
            match = re.search(r'@([^:/?]+)', connection_string)
            if match:
                hostname = match.group(1)
                logger.info(f"🔍 Resolving {hostname} to IPv4...")

                # Resolve to IPv4 only (socket.AF_INET)
                try:
                    addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
                    if addr_info:
                        ipv4_address = addr_info[0][4][0]
                        ipv4_conn_string = connection_string.replace(hostname, ipv4_address)
                        logger.info(f"✅ Resolved {hostname} → {ipv4_address} (IPv4)")
                        logger.info(f"📍 Original: ...@{hostname}...")
                        logger.info(f"📍 Updated:  ...@{ipv4_address}...")
                        return ipv4_conn_string
                    else:
                        logger.error(f"❌ No IPv4 address found for {hostname}")
                        logger.error("⚠️  Using original connection string - IPv6 may fail on Render")
                except socket.gaierror as dns_e:
                    logger.error(f"❌ DNS resolution failed: {dns_e}")
                    logger.error("⚠️  Using original connection string - connection may fail")
            else:
                logger.warning("⚠️  Could not extract hostname from connection string")

            return connection_string

        except Exception as e:
            logger.error(f"❌ IPv4 resolution error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.error("⚠️  Using original connection string - connection may fail")
            return connection_string

    def connect(self) -> psycopg2.extensions.connection:
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                self.connection_string,
                cursor_factory=RealDictCursor
            )
            logger.info("PostgreSQL connection established (read-only for statistics)")
            return self.connection
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def execute_query(self, query: str, params: Tuple = None) -> List[Dict]:
        """Execute SQL query and return results as list of dicts"""
        if not self.connection:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)

                # Check if query returns results
                if cursor.description:
                    results = cursor.fetchall()
                    # Convert RealDictRow to regular dict
                    return [dict(row) for row in results]
                else:
                    return []

        except psycopg2.Error as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
            raise

    def execute_scalar(self, query: str, params: Tuple = None) -> any:
        """Execute SQL query and return single scalar value"""
        if not self.connection:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                if result:
                    # Return first column of first row
                    return list(result.values())[0] if result else None
                return None

        except psycopg2.Error as e:
            logger.error(f"Scalar query execution failed: {e}")
            raise

    def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            if not self.connection:
                self.connect()

            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result:
                    logger.info("✅ Database connection test successful")
                    return True
                return False

        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            return False
