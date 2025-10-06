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

                # Try multiple methods to resolve to IPv4
                ipv4_address = None

                # Method 1: Try subprocess dig with public DNS (most reliable on Linux/Render)
                try:
                    import subprocess
                    logger.info(f"📍 Attempting DNS resolution via dig command with Google DNS...")
                    # Use Google's public DNS 8.8.8.8 to bypass Render's DNS issues
                    result = subprocess.run(
                        ['dig', '@8.8.8.8', '+short', 'A', hostname],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    logger.info(f"📍 dig returncode: {result.returncode}")
                    logger.info(f"📍 dig stdout: '{result.stdout.strip()}'")
                    logger.info(f"📍 dig stderr: '{result.stderr.strip()}'")

                    if result.returncode == 0 and result.stdout.strip():
                        # Take first A record
                        addresses = result.stdout.strip().split('\n')
                        # Filter out any non-IP lines (sometimes dig returns CNAME records)
                        for addr in addresses:
                            addr = addr.strip()
                            if addr and not addr.endswith('.'):  # Not a hostname
                                ipv4_address = addr
                                logger.info(f"✅ Resolved via dig: {hostname} → {ipv4_address} (IPv4)")
                                break
                    else:
                        logger.warning(f"dig returned no results or failed")
                except FileNotFoundError:
                    logger.warning("dig command not found on system")
                except Exception as dig_e:
                    logger.warning(f"dig resolution exception: {dig_e}")

                # Method 2: Try gethostbyname if dig failed
                if not ipv4_address:
                    try:
                        ipv4_address = socket.gethostbyname(hostname)
                        logger.info(f"✅ Resolved via gethostbyname: {hostname} → {ipv4_address} (IPv4)")
                    except socket.gaierror as dns_e:
                        logger.warning(f"gethostbyname resolution failed: {dns_e}")

                # If we got an IPv4 address, use it
                if ipv4_address:
                    ipv4_conn_string = connection_string.replace(hostname, ipv4_address)
                    logger.info(f"📍 Using IPv4 address for connection to avoid Render IPv6 issue")
                    return ipv4_conn_string
                else:
                    logger.error(f"❌ All IPv4 resolution methods failed for {hostname}")
                    logger.error("⚠️  Using original connection string - IPv6 may fail on Render")
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
