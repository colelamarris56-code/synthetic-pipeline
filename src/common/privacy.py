from __future__ import annotations
import json, hashlib
from typing import List, Dict

PRIV = json.loads(open("configs/privacy.json").read())


def token_redact(s: str) -> str:
    """Hash-based tokenization; avoids leaking raw identifiers."""
    return "pt_" + hashlib.sha256(s.encode()).hexdigest()[:10]


def deidentify(records: List[Dict], mode: str | None = None) -> List[Dict]:
    """Apply lightweight de-ID suitable for agent payloads (no PHI)."""
    mode = mode or PRIV["default_mode"]
    out: List[Dict] = []
    for r in records:
        rr = dict(r)
        if "patient_id" in rr and rr["patient_id"] is not None:
            rr["patient_id"] = token_redact(str(rr["patient_id"]))
        # Extend with date shifting, ZIP3 truncation, rare-code suppression, etc.
        out.append(rr)
    return out
