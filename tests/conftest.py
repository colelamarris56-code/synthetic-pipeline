"""Test configuration and fixtures for dashboard app tests."""
import os
from pathlib import Path
from typing import Generator, Any
import pytest
from contextlib import contextmanager

# Add parent directory to Python path to import dashboard_app
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
    import psycopg
    _psycopg_backend = "psycopg"
except ImportError:
    import psycopg2 as psycopg
    _psycopg_backend = "psycopg2"

@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Get test database URL from environment or use default."""
    return os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test_synthetic")

@pytest.fixture
def pg():
    """Create a connection context manager for tests.
    
    This mirrors the pg() function in dashboard_app.py but uses the test database.
    """
    @contextmanager
    def _pg(**kwargs: Any) -> Generator[Any, None, None]:
        """Context manager for database connections."""
        conn = None
        try:
            if _psycopg_backend == "psycopg":
                conn = psycopg.connect(os.getenv("TEST_DATABASE_URL"), **kwargs)
            else:
                conn = psycopg.connect(os.getenv("TEST_DATABASE_URL"), **kwargs)
            yield conn
            conn.commit()
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    return _pg

@pytest.fixture(scope="session", autouse=True)
def setup_test_db(test_db_url: str) -> None:
    """Set up test database schema."""
    os.environ["TEST_DATABASE_URL"] = test_db_url
    
    # Create test tables and initial data
    with psycopg.connect(test_db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP NOT NULL DEFAULT now(),
                    agent_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    rating INTEGER,
                    feedback TEXT
                )
            """)
            conn.commit()

@pytest.fixture(autouse=True)
def cleanup_test_db(pg: Any) -> None:
    """Clean up test data after each test."""
    yield
    with pg() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE reviews RESTART IDENTITY CASCADE")