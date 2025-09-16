from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    pg_dsn: str = os.getenv("PG_DSN", "postgresql://clinic:clinic_pw@127.0.0.1:5432/clinic")
    billing_url: str = os.getenv("BILLING_URL", "http://127.0.0.1:8890").rstrip("/")
    review_url: str = os.getenv("REVIEW_URL", "http://127.0.0.1:8891").rstrip("/")
    account_id: str = os.getenv("SP_ACCOUNT_ID", "00000000-0000-0000-0000-000000000001")
    export_dir: str = os.getenv("SP_EXPORT_DIR", "artifacts/exports")
    feature_monitoring: bool = os.getenv("FEATURE_MONITORING", "1") != "0"


S = Settings()
