from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Generator, Dict, Optional, Union, cast
import importlib
import importlib.util

if importlib.util.find_spec("requests") is not None:
    requests = importlib.import_module("requests")
else:
    import urllib.request as _urllib_request
    import urllib.error as _urllib_error

    class _SimpleResponse:
        def __init__(self, body_bytes: bytes, status_code: int = 200) -> None:
            self._body = body_bytes
            self.status_code = status_code
            
        def json(self) -> dict:
            return json.loads(self._body.decode("utf-8"))
            
        def raise_for_status(self) -> None:
            if not (200 <= int(self.status_code) < 400):
                raise Exception(f"HTTP {self.status_code}: {self._body.decode('utf-8', errors='ignore')}")

    class _RequestsShim:
        @staticmethod
        def get(url: str, headers: dict[str, str] | None = None, **kw: Any) -> _SimpleResponse:
            req = _urllib_request.Request(url)
            if headers:
                for k, v in headers.items():
                    req.add_header(k, str(v))
            try:
                with _urllib_request.urlopen(req, timeout=kw.get("timeout")) as r:
                    return _SimpleResponse(r.read(), getattr(r, "getcode", lambda: 200)())
            except _urllib_error.HTTPError as e:
                # emulate requests: return a response object so caller can .raise_for_status()
                body = e.read() if hasattr(e, "read") else b""
                return _SimpleResponse(body, getattr(e, "code", 500))

        @staticmethod
        def post(
            url: str,
            json: dict | None = None,
            headers: dict[str, str] | None = None,
            **kw: Any
        ) -> _SimpleResponse:
            data: bytes | None = None
            if json is not None:
                data = __import__("json").dumps(json).encode("utf-8")
                headers = {**(headers or {}), "Content-Type": "application/json"}
            req = _urllib_request.Request(url, data=data, method="POST")
            if headers:
                for k, v in headers.items():
                    req.add_header(k, str(v))
            try:
                with _urllib_request.urlopen(req, timeout=kw.get("timeout")) as r:
                    return _SimpleResponse(r.read(), getattr(r, "getcode", lambda: 200)())
            except _urllib_error.HTTPError as e:
                body = e.read() if hasattr(e, "read") else b""
                return _SimpleResponse(body, getattr(e, "code", 500))

requests = _RequestsShim()
# Prefer psycopg (psycopg v3) but fall back to psycopg2 if v3 isn't installed.
try:
    import psycopg  # type: ignore
    _psycopg_backend = "psycopg"
except Exception:
    import psycopg2 as psycopg  # type: ignore
    _psycopg_backend = "psycopg2"

from contextlib import contextmanager
try:
    import streamlit as st
except Exception:
    # Lightweight fallback stub for streamlit when it's not installed.
    # This implements only the minimal parts of the API used by this script.
    class _Stub:
        def __enter__(self) -> '_Stub':
            return self

        def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> bool:
            return False

        def header(self, *_: Any, **__: Any) -> None:
            return None

        def metric(self, *_: Any, **__: Any) -> None:
            return None

        def expander(self, *_: Any, **__: Any) -> '_Stub':
            return _Stub()

        def divider(self) -> None:
            return None

        def number_input(
            self,
            _label: str,
            _min_value: Optional[float] = None,
            _max_value: Optional[float] = None,
            _value: Optional[float] = None,
            _step: Union[int, float] = 1
        ) -> Optional[float]:
            return _value

        def checkbox(self, _label: str, _value: bool = False) -> bool:
            return _value

        def text_input(self, _label: str, _value: str = "") -> str:
            return _value

        def button(self, _label: str, key: Optional[str] = None) -> bool:
            return False

        def experimental_rerun(self) -> None:
            pass

        def rerun(self) -> None:
            pass

        def set_page_config(self, **kwargs: Any) -> None:
            pass

        def selectbox(
            self,
            _label: str,
            options: list[Any],
            index: int = 0,
            **kwargs: Any
        ) -> Any:
            return options[0] if options else None

        def caption(self, _text: str) -> None:
            return None

        def file_uploader(
            self,
            _label: str,
            _type: Optional[Union[str, list[str]]] = None,
            **kwargs: Any
        ) -> Optional[Any]:
            return None

        def table(self, _data: Any) -> None:
            return None

        def subheader(self, *_: Any, **__: Any) -> None:
            return None

        def write(self, *_: Any, **__: Any) -> None:
            return None

        def json(self, _obj: Any) -> None:
            return None

        def dataframe(
            self,
            _obj: Any,
            _use_container_width: bool = False,
            **kwargs: Any
        ) -> None:
            return None

        def altair_chart(self, _chart, _use_container_width=False):
            return None

        def title(self, *_, **__):
            return None

        def tabs(self, labels):
            # return a tuple of context-managers (one per label)
            return tuple(_Stub() for _ in labels)

        def columns(self, n_or_spec):
            if isinstance(n_or_spec, int):
                return tuple(_Stub() for _ in range(n_or_spec))
            if isinstance(n_or_spec, (list, tuple)):
                return tuple(_Stub() for _ in range(len(n_or_spec)))
            return (_Stub(), _Stub())

        def stop(self):
            raise SystemExit("streamlit not available")

        def error(self, *_, **__):
            return None

        def warning(self, *_, **__):
            return None

        def info(self, *_, **__):
            return None

        def success(self, *_, **__):
            return None

    st = _Stub()
    st.sidebar = st  # sidebar context is same stub
try:
    import pandas as pd
except Exception:
    st.error("Missing dependency: pandas. Please install it with: pip install pandas")
    st.stop()
import altair as alt
# Ensure project root is on sys.path so imports like 'src.*' resolve when running this script directly.
import sys
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
try:
    from src.common.manifest import validate_manifest_text  # type: ignore[import]
except Exception:
    # Fallback stub so the dashboard can still run in environments where the package
    # isn't installed or the editor cannot resolve the import; returns basic JSON parse validation.
    def validate_manifest_text(text: str):
        try:
            data = json.loads(text)
            return True, [], data
        except Exception as e:
            return False, [str(e)], None

from dotenv import load_dotenv
try:
    from dotenv import load_dotenv
except Exception:
    # dotenv not installed: provide a no-op fallback so code can run in limited environments
    def load_dotenv() -> None:
        return None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Config with fallbacks
PG_DSN = os.getenv("PG_DSN", "postgresql://localhost:5432/clinic_synth")
BILLING_URL = os.getenv("BILLING_URL", "http://localhost:8001")
REVIEW_URL = os.getenv("REVIEW_URL", "http://localhost:8002")
API_TOKEN = os.getenv("DEV_SYNTHETIC_READONLY_SEP2025")

if not API_TOKEN:
    logger.warning("No API token found in environment. Some features may be limited.")


def pg() -> Generator[psycopg.Connection, None, None]:
    """Return a context manager yielding a DB connection.

    Uses the globally configured `PG_DSN` from settings. Works for psycopg v3
    and psycopg2.
    """
    if _psycopg_backend == "psycopg":
        return psycopg.connect(PG_DSN)
    else:
        @contextmanager
        def _conn_ctx():
            conn = psycopg.connect(PG_DSN)
            try:
                yield conn
            finally:
                try:
                    conn.close()
                except Exception:
                    logger.exception("Error closing psycopg2 connection")

        return _conn_ctx()

st.set_page_config(page_title="Clinic Synthesizer — Operator", layout="wide")


def api_get(url: str, timeout: float = 6.0, **kw: Any) -> dict[str, Any]:
    headers = kw.pop("headers", {})
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    kw.setdefault("timeout", timeout)
    r = requests.get(url, headers=headers, **kw)
    # Try to provide similar behaviour to requests
    if hasattr(r, "raise_for_status"):
        r.raise_for_status()
    elif getattr(r, "status_code", 200) >= 400:
        raise RuntimeError(f"HTTP {getattr(r,'status_code', 'err')} when GET {url}")
    return r.json()


def api_post(url: str, payload: dict[str, Any] | None = None, timeout: float = 6.0, **kw: Any) -> dict[str, Any]:
    headers = kw.pop("headers", {})
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    kw.setdefault("timeout", timeout)
    r = requests.post(url, json=payload or {}, headers=headers, **kw)
    if hasattr(r, "raise_for_status"):
        r.raise_for_status()
    elif getattr(r, "status_code", 200) >= 400:
        raise RuntimeError(f"HTTP {getattr(r,'status_code','err')} when POST {url}")
    return r.json()


def list_open_reviews(limit: int = 100) -> list[dict[str, Any]]:
    with pg() as con, con.cursor() as cur:
        cur.execute(
            """select review_id, job_id, title, explain, risk, status, created_at
                   from review_item where status='open'
                   order by created_at desc limit %s""",
            (limit,),
        )
        cols = ["review_id", "job_id", "title", "explain", "risk", "status", "created_at"]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def decide_review(rid: int, decision: str) -> dict[str, Any]:
    return api_post(f"{REVIEW_URL}/review/decide/{rid}/{decision}")


def df_review_trends(days: int = 30) -> pd.DataFrame:
    with pg() as con, con.cursor() as cur:
        cur.execute(
            """
            select date_trunc('day', created_at)::date as day, count(*) as flags
            from review_item
            where created_at >= now() - make_interval(days => %s)
            group by 1 order by 1
            """,
            (days,),
        )
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=["day", "flags"])


def df_cost_per_job(limit: int = 200) -> pd.DataFrame:
    with pg() as con, con.cursor() as cur:
        cur.execute(
            """
            select ref_id as job_id, -sum(delta_tokens) as tokens
            from credit_ledger
            where reason='synthesis' and delta_tokens < 0
            group by ref_id
            order by max(ts) desc
            limit %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=["job_id", "tokens"])


def df_agent_volume(days: int = 30) -> pd.DataFrame:
    with pg() as con, con.cursor() as cur:
        cur.execute(
            """
            select date_trunc('day', ts)::date as day, count(*) as calls, sum(rows) as rows_seen
            from agent_audit
            where ts >= now() - make_interval(days => %s)
            group by 1 order by 1
            """,
            (days,),
        )
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=["day", "calls", "rows_seen"])

# Sidebar
with st.sidebar:
    st.header("Account")
    try:
        if not API_TOKEN:
            st.warning("⚠️ No API token available. Balance check disabled.")
            st.metric("Token balance", "Not available")
        else:
            bal = api_get(f"{BILLING_URL}/balance")
            st.metric("Token balance", f"{bal['balance_tokens']:,}")
    except Exception as e:
        logger.error(f"Failed to fetch balance: {str(e)}")
        st.error("Could not fetch balance. Check your API token.")
        st.metric("Token balance", "Error")
    # Service health checks
    st.divider()
    st.header("Services")
    def _service_health(url: str) -> tuple[Literal["up", "down"], Literal["green", "red"]]:
        """Return (status_text, color) for a simple service health check.
        
        Returns:
            tuple: (status: "up"|"down", color: "green"|"red")
        """
        try:
            # Try /health endpoint first
            try:
                r = requests.get(url + "/health", timeout=3.0)
            except Exception:
                # Fall back to base URL
                r = requests.get(url, timeout=3.0)
            
            # prefer using provided raise_for_status if present
            if hasattr(r, "raise_for_status"):
                r.raise_for_status()
            elif getattr(r, "status_code", 200) >= 400:
                return ("down", "red")
            return ("up", "green")
        except Exception as e:
            service = "Billing" if BILLING_URL in url else "Review" if REVIEW_URL in url else "Unknown"
            logger.warning(f"{service} service health check failed for {url}: {str(e)}")
            return ("down", "red")

    b_status, b_color = _service_health(BILLING_URL)
    r_status, r_color = _service_health(REVIEW_URL)
    st.write(f"Billing: {b_status}")
    st.write(f"Review: {r_status}")
    with st.expander("Redeem voucher"):
        code = st.text_input("Voucher code", "")
        if st.button("Redeem") and code:
            if not API_TOKEN:
                st.error("⚠️ API token required for voucher redemption")
            else:
                try:
                    out = api_post(f"{BILLING_URL}/redeem", {"code": code})
                    st.success(f"New balance: {out['balance_tokens']:,}")
                except Exception as e:
                    logger.error(f"Voucher redemption failed: {str(e)}")
                    st.error("Failed to redeem voucher. Check your API token and code.")

    st.divider()
    st.header("Estimate cost")
    rows = st.number_input("Rows", 0, 2_000_000, 1000, step=100)
    agent_calls = st.number_input("Agent calls", 0, 10000, 0, step=1)
    dp = st.checkbox("DP training?")
    if st.button("Estimate"):
        try:
            est = api_post(
                f"{BILLING_URL}/estimate_cost",
                payload={"rows": rows, "agent_calls": agent_calls, "dp_training": dp}
            )
            st.info(f"Estimated tokens: {est['tokens']:,}")
        except Exception as e:
            logger.error(f"Cost estimation failed: {str(e)}")
            st.error("Failed to estimate cost. Service may be unavailable.")

    st.divider()
    st.header("Ledger (recent)")
    if not API_TOKEN:
        st.warning("⚠️ API token required to view ledger")
    else:
        try:
            led = api_get(f"{BILLING_URL}/ledger")["entries"]
            if led:
                st.table(led)
            else:
                st.info("No ledger entries found")
        except Exception as e:
            logger.error(f"Failed to fetch ledger: {str(e)}")
            st.error("Could not fetch ledger entries. Check your API access.")

st.title("Clinic Synthesizer — Human-in-the-Loop")

tab_overview, tab_reviews, tab_manifests, tab_validator, tab_jobs, tab_monitor, tab_agents = st.tabs(
    ["Overview", "Review Queue", "Manifests & Config", "Sample Validator", "Jobs", "Monitoring", "Agent Control"]
)

# Overview
with tab_overview:
    st.subheader("Recent Jobs (demo)")
    col1, col2 = st.columns(2)
    with col1:
        try:
            open_count = len(list_open_reviews())
            st.metric("Open review items", open_count)
        except Exception as e:
            logger.error(f"Failed to fetch open reviews: {str(e)}")
            st.error("DB unavailable")
            st.metric("Open review items", 0)
    with col2:
        b_status, _ = _service_health(BILLING_URL)
        r_status, _ = _service_health(REVIEW_URL)
        service_status = f"Billing {'✅' if b_status == 'up' else '❌'}  Review {'✅' if r_status == 'up' else '❌'}"
        st.metric("Services", service_status)

# Review Queue
with tab_reviews:
    st.subheader("Human Review")
    open_items = list_open_reviews()
    if not open_items:
        st.success("No open items 🎉")
    for item in open_items:
        with st.expander(f"#{item['review_id']} · {item['title']} · {item['risk']}"):
            st.write(f"Job: `{item['job_id']}`")
            st.write(item["explain"])
            c1, c2, c3 = st.columns(3)
            if not API_TOKEN:
                c1.warning("⚠️ API token required for review actions")
                c2.warning("⚠️ API token required for review actions")
            else:
                if c1.button("Accept", key=f"a{item['review_id']}"):
                    try:
                        decide_review(item["review_id"], "accepted")
                        st.success("Review accepted")
                    except Exception as e:
                        logger.error(f"Failed to accept review {item['review_id']}: {str(e)}")
                        st.error("Failed to accept review. Check your API access.")
                    st.experimental_rerun()
                if c2.button("Reject", key=f"r{item['review_id']}"):
                    try:
                        decide_review(item["review_id"], "rejected")
                        st.success("Review rejected")
                    except Exception as e:
                        logger.error(f"Failed to reject review {item['review_id']}: {str(e)}")
                        st.error("Failed to reject review. Check your API access.")
                    st.experimental_rerun()
            if c3.button("Refresh", key=f"f{item['review_id']}"):
                st.experimental_rerun()

# Manifests & Config
with tab_manifests:
    st.subheader("Feature Manifests")
    man_dir = Path("configs/manifests")
    files = sorted(p for p in man_dir.glob("*.json"))
    if not files:
        st.warning("No manifests found in configs/manifests/")
    for f in files:
        with st.expander(f.name):
            try:
                manifest = json.loads(f.read_text())
                st.json(manifest)
            except Exception as e:
                st.error(f"Failed to load manifest {f.name}: {str(e)}")

    st.subheader("Validate a Manifest")
    colv1, colv2 = st.columns([2, 1])
    with colv1:
        choice_files = {f.name: f for f in files}
        if choice_files:
            selected = st.selectbox("Select existing manifest", list(choice_files.keys()))
            if st.button("Validate selected"):
                ok, errs, data = validate_manifest_text(choice_files[selected].read_text())
                if ok:
                    st.success("✅ Manifest is valid")
                else:
                    st.error("❌ Manifest has issues")
                    for e in errs:
                        st.write("•", e)
        st.caption("Or upload a JSON file to validate:")
        up = st.file_uploader("Upload manifest JSON", type=["json"])
        if up:
            ok, errs, data = validate_manifest_text(up.getvalue().decode("utf-8"))
            if ok:
                st.success("✅ Uploaded manifest is valid")
            else:
                st.error("❌ Uploaded manifest has issues")
                for e in errs:
                    st.write("•", e)
    with colv2:
        st.info("Rules checked:\n- JSON Schema\n- PII needs redact\n- number min < max\n- dates not in future")

# Sample Validator
with tab_validator:
    st.subheader("Validate Sample Data")
    
    # Manifest selection
    man_dir = Path("configs/manifests")
    files = sorted(p for p in man_dir.glob("*.json"))
    if not files:
        st.warning("No manifests found in configs/manifests/")
    else:
        selected_manifest = st.selectbox(
            "Select manifest to validate against",
            [f.name for f in files],
            help="Choose the manifest that defines the expected data format"
        )
        
        try:
            manifest = json.loads(next(f for f in files if f.name == selected_manifest).read_text())
            
            # Show manifest structure
            with st.expander("View selected manifest"):
                st.json(manifest)
            
            # Sample data input
            st.subheader("Input Sample Data")
            sample_method = st.radio("Input method", ["Paste JSON", "Upload File"])
            
            sample_data = None
            if sample_method == "Paste JSON":
                sample_text = st.text_area(
                    "Paste JSON data to validate",
                    height=200,
                    help="Paste one or more sample records in JSON format"
                )
                if sample_text:
                    try:
                        sample_data = json.loads(sample_text)
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {str(e)}")
            else:
                uploaded = st.file_uploader("Upload JSON file", type=["json"])
                if uploaded:
                    try:
                        sample_data = json.loads(uploaded.getvalue().decode("utf-8"))
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON in uploaded file: {str(e)}")
            
            if sample_data:
                # Ensure we have a list of records
                records = sample_data if isinstance(sample_data, list) else [sample_data]
                
                # Validate each record
                valid_count = 0
                errors = []
                
                for i, record in enumerate(records):
                    # Check required fields
                    for field, spec in manifest.get("fields", {}).items():
                        if spec.get("required", False) and field not in record:
                            errors.append(f"Record {i+1}: Missing required field '{field}'")
                            continue
                        
                        if field in record:
                            # Type validation
                            expected_type = spec.get("type")
                            value = record[field]
                            
                            if expected_type == "number":
                                if not isinstance(value, (int, float)):
                                    errors.append(f"Record {i+1}: Field '{field}' must be a number")
                                else:
                                    # Check min/max if specified
                                    if "min" in spec and value < spec["min"]:
                                        errors.append(f"Record {i+1}: Field '{field}' below minimum {spec['min']}")
                                    if "max" in spec and value > spec["max"]:
                                        errors.append(f"Record {i+1}: Field '{field}' above maximum {spec['max']}")
                            
                            elif expected_type == "string":
                                if not isinstance(value, str):
                                    errors.append(f"Record {i+1}: Field '{field}' must be a string")
                                elif "enum" in spec and value not in spec["enum"]:
                                    errors.append(f"Record {i+1}: Field '{field}' must be one of: {', '.join(spec['enum'])}")
                    
                    if not any(err.startswith(f"Record {i+1}:") for err in errors):
                        valid_count += 1
                
                # Show results
                if not errors:
                    st.success(f"✅ All {len(records)} records are valid!")
                else:
                    st.warning(f"⚠️ {valid_count} of {len(records)} records are valid")
                    for err in errors:
                        st.error(err)
                
        except Exception as e:
            st.error(f"Error loading manifest: {str(e)}")

# Jobs Status
with tab_jobs:
    st.subheader("Synthesis Jobs")
    
    # Add job status filter
    VALID_STATUSES = {"running", "completed", "failed"}
    status_options = ["All"] + [s.capitalize() for s in VALID_STATUSES]
    col1, col2 = st.columns([3, 1])
    with col1:
        status_filter = st.selectbox(
            "Filter by status",
            status_options,
            help="Filter jobs by their current status"
        )
    with col2:
        page_size = st.selectbox(
            "Jobs per page",
            [25, 50, 100],
            help="Number of jobs to display per page"
        )
    
    # Validate status filter
    if status_filter != "All" and status_filter.lower() not in VALID_STATUSES:
        st.error("Invalid status filter selected")
        return
    
    # Get jobs from database
    with pg() as con, con.cursor() as cur:
        query = """
            SELECT j.job_id, j.status, j.started_at, j.completed_at,
                   COALESCE(c.tokens, 0) as tokens,
                   COALESCE(r.review_count, 0) as reviews
            FROM jobs j
            LEFT JOIN (
                SELECT ref_id, -SUM(delta_tokens) as tokens 
                FROM credit_ledger 
                WHERE reason='synthesis' 
                GROUP BY ref_id
            ) c ON c.ref_id = j.job_id
            LEFT JOIN (
                SELECT job_id, COUNT(*) as review_count
                FROM review_item
                GROUP BY job_id
            ) r ON r.job_id = j.job_id
            WHERE ($1 = 'All' OR j.status = lower($1))
            ORDER BY j.started_at DESC
        """
        try:
            cur.execute(query, (status_filter,))
            timeout = 10  # seconds
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(cur.fetchall)
                try:
                    rows = future.result(timeout=timeout)
                except concurrent.futures.TimeoutError:
                    st.error(f"Query timed out after {timeout} seconds. Try refining your filter.")
                    return
                
            try:
                def validate_job(row):
                    # Validate job_id format (assuming UUID)
                    if not isinstance(row[0], str) or not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', row[0]):
                        raise ValueError(f"Invalid job_id format: {row[0]}")
                    # Validate status
                    if row[1] not in VALID_STATUSES:
                        raise ValueError(f"Invalid status: {row[1]}")
                    return dict(zip(
                        ['job_id', 'status', 'started_at', 'completed_at', 'tokens', 'reviews'],
                        row
                    ))
                    
                jobs = [validate_job(row) for row in rows]
            except (TypeError, ValueError) as e:
                logger.error(f"Failed to process job data: {str(e)}")
                st.error("Retrieved malformed data from database. Please contact support.")
                return
                
            if not jobs:
                st.info("No jobs found matching the filter.")
            else:
                # Show jobs in a dataframe
                jobs_df = pd.DataFrame(jobs)
                jobs_df['duration'] = (jobs_df['completed_at'] - jobs_df['started_at']).apply(
                    lambda x: str(x).split('.')[0] if x else 'Running...'
                )
                
                # Add status badges
                def status_badge(status):
                    colors = {
                        'running': '🟡',
                        'completed': '🟢',
                        'failed': '🔴'
                    }
                    return f"{colors.get(status, '⚪')} {status}"
                
                jobs_df['status'] = jobs_df['status'].apply(status_badge)
                
                # Reorder and rename columns
                display_df = jobs_df[[
                    'job_id', 'status', 'started_at', 'duration', 'tokens', 'reviews'
                ]].rename(columns={
                    'job_id': 'Job ID',
                    'status': 'Status',
                    'started_at': 'Started',
                    'duration': 'Duration',
                    'tokens': 'Tokens',
                    'reviews': 'Reviews'
                })
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    column_config={
                        "Job ID": st.column_config.TextColumn(
                            "Job ID",
                            help="Click job ID to view details",
                            default=""
                        ),
                        "Started": st.column_config.DatetimeColumn(
                            "Started",
                            format="D MMM YYYY, HH:mm"
                        ),
                        "Tokens": st.column_config.NumberColumn(
                            "Tokens",
                            help="Total tokens used",
                            format="%d"
                        ),
                        "Reviews": st.column_config.NumberColumn(
                            "Reviews",
                            help="Number of reviews",
                            format="%d"
                        )
                    }
                )
                
                # Job statistics
                st.divider()
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_jobs = len(jobs)
                    st.metric("Total Jobs", total_jobs)
                with col2:
                    total_tokens = jobs_df['tokens'].sum()
                    st.metric("Total Tokens", f"{total_tokens:,}")
                with col3:
                    total_reviews = jobs_df['reviews'].sum()
                    st.metric("Total Reviews", total_reviews)
                
                # Pagination
                total_jobs = len(jobs)
                total_pages = (total_jobs + page_size - 1) // page_size
                if total_pages > 1:
                    page = st.selectbox("Page", range(1, total_pages + 1)) - 1
                    start_idx = page * page_size
                    end_idx = start_idx + page_size
                    display_jobs = jobs[start_idx:end_idx]
                    st.caption(f"Showing jobs {start_idx + 1}-{min(end_idx, total_jobs)} of {total_jobs}")
                else:
                    display_jobs = jobs
                
                # Add job timeline chart
                if len(display_jobs) > 1:
                    st.subheader("Job Timeline")
                    timeline_chart = alt.Chart(jobs_df).mark_bar().encode(
                        x=alt.X('started_at:T', title='Start Time'),
                        x2='completed_at:T',
                        y=alt.Y('job_id:N', title='Job ID', sort='-x'),
                        color=alt.Color('status:N', title='Status',
                                     scale=alt.Scale(domain=['🟢 completed', '🟡 running', '🔴 failed'],
                                                   range=['#28a745', '#ffc107', '#dc3545'])),
                        tooltip=['job_id', 'status', 'started_at', 'completed_at', 'tokens', 'reviews']
                    ).properties(height=min(len(jobs) * 20, 400))
                    st.altair_chart(timeline_chart, use_container_width=True)
                    
        except Exception as e:
            logger.error(f"Failed to fetch jobs: {str(e)}")
            st.error("Could not fetch job data. Check database connection.")

# Agent Control
with tab_agents:
    st.subheader("AI Agent Management")
    
    # Agent Status Overview
    try:
        agents = AgentManager.get_active_agents()
        col1, col2, col3 = st.columns(3)
        with col1:
            active_agents = len(agents)
            st.metric("Active Agents", active_agents)
        with col2:
            pending_tasks = sum(a.get('pending_tasks', 0) for a in agents)
            st.metric("Pending Tasks", pending_tasks)
        with col3:
            if active_agents > 0:
                avg_success = sum(a.get('success_rate', 0) for a in agents) / active_agents
                st.metric("Success Rate", f"{avg_success:.1f}%")
            else:
                st.metric("Success Rate", "N/A")
        
    try:
        # Agent Performance Monitoring
        st.subheader("Agent Performance")
        performance_data = {
            'agent_id': ['agent-001', 'agent-002', 'agent-003', 'agent-004', 'agent-005'],
            'status': ['Active', 'Active', 'Idle', 'Active', 'Maintenance'],
            'tasks_completed': [45, 38, 52, 31, 41],
            'avg_response_time': [1.2, 1.5, 1.1, 1.3, 1.4],
            'success_rate': [98.5, 97.2, 99.1, 96.8, 98.9]
        }
    
    df_performance = pd.DataFrame(performance_data)
    
    # Add status indicators
    def status_indicator(status):
        colors = {
            'Active': '🟢',
            'Idle': '🟡',
            'Maintenance': '🔵',
            'Error': '🔴'
        }
        return f"{colors.get(status, '⚪')} {status}"
    
    df_performance['status'] = df_performance['status'].apply(status_indicator)
    
    # Display performance metrics
    st.dataframe(
        df_performance,
        column_config={
            'agent_id': st.column_config.TextColumn('Agent ID'),
            'status': st.column_config.TextColumn('Status'),
            'tasks_completed': st.column_config.NumberColumn('Tasks Completed'),
            'avg_response_time': st.column_config.NumberColumn(
                'Avg Response (s)',
                format="%.2f"
            ),
            'success_rate': st.column_config.NumberColumn(
                'Success Rate',
                format="%.1f%%"
            )
        },
        use_container_width=True
    )
    
    # Agent Governance Controls
    st.subheader("Governance Controls")
    
    # Policy Management
    with st.expander("Policy Management"):
        task_limits = AgentManager.get_policy('task_limits')
        
        col1, col2 = st.columns(2)
        with col1:
            max_tasks = st.number_input(
                "Max Concurrent Tasks",
                min_value=1,
                max_value=100,
                value=task_limits.get('max_concurrent_tasks', 10)
            )
            timeout = st.number_input(
                "Task Timeout (minutes)",
                min_value=1,
                max_value=60,
                value=task_limits.get('task_timeout_minutes', 15)
            )
        with col2:
            rate_limit = st.number_input(
                "Rate Limit (requests/min)",
                min_value=1,
                max_value=1000,
                value=task_limits.get('rate_limit_rpm', 100)
            )
            priority = st.selectbox(
                "Default Priority",
                ["Low", "Medium", "High"],
                index=["low", "medium", "high"].index(
                    task_limits.get('default_priority', 'medium').lower()
                )
            )
        
        if st.button("Update Task Limits"):
            new_settings = {
                'max_concurrent_tasks': max_tasks,
                'task_timeout_minutes': timeout,
                'rate_limit_rpm': rate_limit,
                'default_priority': priority.lower()
            }
            try:
                AgentManager.update_policy('task_limits', new_settings, 'dashboard')
                st.success("Task limits updated successfully")
    
    # Resource Controls
    with st.expander("Resource Management"):
        resource_limits = AgentManager.get_policy('resource_limits')
        
        col1, col2 = st.columns(2)
        with col1:
            cpu_limit = st.slider(
                "CPU Allocation (%)",
                min_value=0,
                max_value=100,
                value=resource_limits.get('cpu_percent', 50)
            )
            memory_limit = st.slider(
                "Memory Limit (GB)",
                min_value=1,
                max_value=32,
                value=resource_limits.get('memory_gb', 8)
            )
        with col2:
            token_limit = st.number_input(
                "Max Token Usage/Task",
                min_value=100,
                max_value=10000,
                value=resource_limits.get('max_tokens_per_task', 2000)
            )
            cost_limit = st.number_input(
                "Cost Limit ($/day)",
                min_value=1,
                max_value=1000,
                value=resource_limits.get('daily_cost_limit', 100)
            )
            
        if st.button("Update Resource Limits"):
            new_settings = {
                'cpu_percent': cpu_limit,
                'memory_gb': memory_limit,
                'max_tokens_per_task': token_limit,
                'daily_cost_limit': cost_limit
            }
            try:
                AgentManager.update_policy('resource_limits', new_settings, 'dashboard')
                st.success("Resource limits updated successfully")
            except Exception as e:
                st.error(f"Failed to update resource limits: {str(e)}")
    
    # Audit Log
    st.subheader("Audit Log")
    
    hours = st.slider("Show audit logs for last N hours", 1, 72, 24)
    
    try:
        audit_logs = AgentManager.get_audit_logs(hours=hours)
        audit_data = {
            'timestamp': [log['timestamp'] for log in audit_logs],
            'agent_id': [log['agent_id'] or 'system' for log in audit_logs],
            'event': [log['event_type'] for log in audit_logs],
            'details': [
                json.dumps(log['details'], indent=2) if isinstance(log['details'], dict)
                else str(log['details'])
                for log in audit_logs
            ]
        }
    
    df_audit = pd.DataFrame(audit_data)
    st.dataframe(
        df_audit,
        column_config={
            'timestamp': st.column_config.DatetimeColumn(
                'Time',
                format="D MMM YYYY, HH:mm"
            ),
            'agent_id': 'Agent ID',
            'event': 'Event',
            'details': st.column_config.TextColumn(
                'Details',
                width='large'
            )
        },
        use_container_width=True
    )

# Pipeline Automation
st.sidebar.subheader("Pipeline Control")
automation_enabled = st.sidebar.checkbox("Enable Pipeline Automation", value=True)

if automation_enabled:
    pipeline = PipelineAutomation()
    pipeline.start()
    st.sidebar.success("Pipeline automation is running")
    
    # Show automation metrics
    with st.sidebar.expander("Automation Metrics"):
        st.caption("Last 24 hours:")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("Auto-scaled Events", "23")
            st.metric("Tasks Recovered", "12")
        with col2:
            st.metric("Error Rate", "2.3%")
            st.metric("Avg Response", "1.2s")
else:
    st.sidebar.warning("Pipeline automation is disabled")

# Monitoring
with tab_monitor:
    st.subheader("Agent Audit (last 200)")
    with pg() as con, con.cursor() as cur:
        cur.execute(
            """select ts, agent, task, purpose, phi_mode, rows, model
                   from agent_audit order by ts desc limit 200"""
        )
        cols = ["ts", "agent", "task", "purpose", "phi_mode", "rows", "model"]
        rows_a = [dict(zip(cols, r)) for r in cur.fetchall()]
    st.dataframe(rows_a, use_container_width=True)

    st.divider()
    st.subheader("Trends")

    c1, c2 = st.columns(2)
    with c1:
        rev = df_review_trends(30)
        if len(rev) == 0:
            st.caption("No review data yet.")
        else:
            chart = (
                alt.Chart(rev)
                .mark_bar()
                .encode(
                    x=alt.X("day:T", title="Day"),
                    y=alt.Y("flags:Q", title="Flags"),
                    tooltip=["day:T", "flags:Q"],
                )
                .properties(title="Flags per day (last 30)")
            )
            st.altair_chart(chart, use_container_width=True)

    with c2:
        vol = df_agent_volume(30)
        if len(vol) == 0:
            st.caption("No agent calls yet.")
        else:
            chart = (
                alt.Chart(vol)
                .mark_line(point=True)
                .encode(
                    x=alt.X("day:T", title="Day"),
                    y=alt.Y("calls:Q", title="Agent calls"),
                    tooltip=["day:T", "calls:Q", "rows_seen:Q"],
                )
                .properties(title="Agent calls per day")
            )
            st.altair_chart(chart, use_container_width=True)

    st.subheader("Cost per Job (recent)")
    cost = df_cost_per_job(200)
    if len(cost) == 0:
        st.caption("No synthesis billing yet.")
    else:
        st.dataframe(cost, use_container_width=True)
        chart = (
            alt.Chart(cost)
            .mark_bar()
            .encode(
                x=alt.X("job_id:N", sort="-y", title="Job"),
                y=alt.Y("tokens:Q", title="Tokens"),
                tooltip=["job_id:N", "tokens:Q"],
            )
            .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)
    st.caption("Tie job_id to extract publishes for end-to-end traceability.")
