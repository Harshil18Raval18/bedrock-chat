"""RDS PostgreSQL connection management with pgvector support."""

import os
import logging
from typing import Optional
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RDSVectorStore:
    """Manages connections to RDS PostgreSQL with pgvector extension."""

    _instance: Optional["RDSVectorStore"] = None
    _connection_pool: Optional[pool.SimpleConnectionPool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize RDS connection pool."""
        if self._connection_pool is None:
            self._init_connection_pool()

    @staticmethod
    def _init_connection_pool():
        """Initialize connection pool to RDS."""
        try:
            rds_host = os.getenv("RDS_HOST")
            rds_port = os.getenv("RDS_PORT", "5432")
            rds_database = os.getenv("RDS_DATABASE", "postgres")
            rds_user = os.getenv("RDS_USER", "postgres")
            rds_password = os.getenv("RDS_PASSWORD")

            if not all([rds_host, rds_user, rds_password]):
                raise ValueError("Missing RDS connection environment variables")

            RDSVectorStore._connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=rds_host,
                port=int(rds_port),
                database=rds_database,
                user=rds_user,
                password=rds_password,
                sslmode="require",
            )
            logger.info("RDS connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RDS connection pool: {str(e)}")
            raise

    def get_connection(self):
        """Get a connection from the pool."""
        if self._connection_pool is None:
            self._init_connection_pool()
        return self._connection_pool.getconn()

    def return_connection(self, conn):
        """Return a connection to the pool."""
        if self._connection_pool:
            self._connection_pool.putconn(conn)

    def close_all_connections(self):
        """Close all connections in the pool."""
        if self._connection_pool:
            self._connection_pool.closeall()
            self._connection_pool = None
            logger.info("All RDS connections closed")

    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False):
        """Execute a query and return results."""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params or ())
                if fetch_one:
                    return cur.fetchone()
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            raise
        finally:
            if conn:
                self.return_connection(conn)

    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute an insert/update/delete query."""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                conn.commit()
                return cur.rowcount
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Update execution error: {str(e)}")
            raise
        finally:
            if conn:
                self.return_connection(conn)

    def execute_batch(self, query: str, params_list: list) -> int:
        """Execute batch insert/update operations."""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                for params in params_list:
                    cur.execute(query, params)
                conn.commit()
                return cur.rowcount
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Batch execution error: {str(e)}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
