"""
Database connection manager for PostgreSQL (read-only statistics queries)

Note: This module uses direct PostgreSQL connection for complex aggregation queries.
The main data pipeline (live_odds, historical_odds) uses Supabase client for write operations.
"""
import logging
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages PostgreSQL database connections for read-only statistics queries"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None

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
