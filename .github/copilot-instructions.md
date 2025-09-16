# Synthetic Pipeline AI Agent Instructions

## Project Overview
This project implements a synthetic data generation pipeline with a Streamlit dashboard for monitoring and control. The system consists of multiple microservices handling billing, reviews, and data generation.

## Core Architecture
- `scripts/dashboard_app.py`: Central monitoring dashboard with Streamlit UI
- `app/db.py`: Database access layer and connection management
- Services communicate via HTTP with bearer token auth
- Environment-based configuration (DB, API endpoints, tokens)

## Key Design Patterns
1. **Resilient Imports**
```python
# Use conditional imports with fallbacks for optional dependencies
if importlib.util.find_spec("requests") is not None:
    requests = importlib.import_module("requests")
else:
    # Fall back to urllib-based shim
```

2. **Database Connection Management**
```python
@contextmanager
def pg():
    """Return a context manager yielding a DB connection."""
    with psycopg.connect(PG_DSN) as conn:
        yield conn
```

3. **API Error Handling**
```python
def api_get(url, timeout=6.0, **kw):
    headers = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}
    r = requests.get(url, headers=headers, timeout=timeout, **kw)
    r.raise_for_status()
    return r.json()
```

## Development Workflow
1. Run dashboard locally:
   ```
   streamlit run scripts/dashboard_app.py
   ```
2. Testing:
   - Tests use pytest with both in-memory and Docker Postgres options
   - Run `pytest tests/` for unit tests

## Integration Points
- **Billing Service**: `BILLING_URL` (default: http://localhost:8001)
- **Review Service**: `REVIEW_URL` (default: http://localhost:8002)  
- **Database**: Configure via `PG_DSN` environment variable
- **API Token**: Set `DEV_SYNTHETIC_READONLY_SEP2025` for authenticated endpoints

## Error Handling Conventions
1. Service health checks should probe /health first, then fall back to base URL
2. Use safe_rerun() helper for Streamlit error recovery
3. Wrap DB operations in proper connection context managers
4. Log failures before triggering Streamlit reruns

## Code Style
- Type hints are used throughout new code
- Follow existing patterns for conditional imports and stubs
- Use ruff for linting and black for formatting
- Pre-commit hooks enforce style guidelines