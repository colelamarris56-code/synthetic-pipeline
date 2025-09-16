"""
Database connection handling for the Clinic Synthesizer Operator.
Provides a unified connection helper with proper error management.
"""
from contextlib import contextmanager
from typing import Generator, Any
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .settings import config

# Global connection pool
pool = ConnectionPool(
    conninfo=config.db_url,
    min_size=1,
    max_size=10,
    kwargs={"row_factory": dict_row}
)

class DatabaseError(Exception):
    """Base exception for database-related errors."""
    pass

@contextmanager
def pg() -> Generator[psycopg.Connection, None, None]:
    """
    Context manager for database connections.
    Handles proper connection acquisition and release.
    
    Usage:
        with pg() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM table")
                results = cur.fetchall()
    
    Raises:
        DatabaseError: On connection or query errors
    """
    try:
        conn = pool.getconn()
        try:
            yield conn
            conn.commit()
        except psycopg.Error as e:
            conn.rollback()
            raise DatabaseError(f"Database operation failed: {str(e)}") from e
        finally:
            pool.putconn(conn)
    except psycopg.Error as e:
        raise DatabaseError(f"Failed to connect to database: {str(e)}") from e

def query_one(sql: str, params: tuple[Any, ...] = ()) -> dict:
    """
    Execute a query and return a single row as a dictionary.
    
    Args:
        sql: SQL query string
        params: Query parameters
        
    Returns:
        dict: Single row result
        
    Raises:
        DatabaseError: If query fails or no results found
    """
    with pg() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            result = cur.fetchone()
            if result is None:
                raise DatabaseError("No results found")
            return result

def query_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict]:
    """
    Execute a query and return all rows as a list of dictionaries.
    
    Args:
        sql: SQL query string
        params: Query parameters
        
    Returns:
        list[dict]: List of row results
        
    Raises:
        DatabaseError: If query fails
    """
    with pg() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def execute(sql: str, params: tuple[Any, ...] = ()) -> None:
    """
    Execute a query without returning results (INSERT, UPDATE, DELETE).
    
    Args:
        sql: SQL query string
        params: Query parameters
        
    Raises:
        DatabaseError: If query fails
    """
    with pg() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)