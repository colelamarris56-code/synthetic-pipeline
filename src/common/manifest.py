from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Tuple
from jsonschema import Draft202012Validator

SCHEMA_PATH = Path("configs/schemas/manifest.schema.json")


def load_schema() -> Dict:
    return json.loads(SCHEMA_PATH.read_text())


def validate_manifest_text(text: str) -> Tuple[bool, List[str], Dict]:
    schema = load_schema()
    data = json.loads(text)
    v = Draft202012Validator(schema)
    errs = [f"{'.'.join([str(p) for p in e.path])}: {e.message}" for e in v.iter_errors(data)]

    extras: List[str] = []
    if "schema" in data:
        for field, spec in data["schema"].items():
            if spec.get("type") == "number":
                mi, ma = spec.get("min"), spec.get("max")
                if mi is not None and ma is not None and mi >= ma:
                    extras.append(f"{field}: min >= max ({mi} >= {ma})")
            if spec.get("pii") and spec.get("redact") not in {"token", "drop"}:
                extras.append(f"{field}: pii=true must have redact='token' or 'drop'")
            if spec.get("type") == "date" and spec.get("not_future") is not True:
                extras.append(f"{field}: date fields should set not_future=true")

    all_errs = errs + extras
    ok = len(all_errs) == 0
    return ok, all_errs, data
