from src.common.manifest import validate_manifest_text
import json


def test_schema_valid():
    manifest = {
        "extract_id": "t2d_care_gaps_v3",
        "purpose": "operations",
        "phi_mode": "expert",
        "schema": {
            "patient_id": {"type": "string", "pii": True, "redact": "token"},
            "last_hba1c_value": {"type": "number", "min": 3.5, "max": 20},
            "last_hba1c_date": {"type": "date", "not_future": True},
        },
    }
    ok, errs, _ = validate_manifest_text(json.dumps(manifest))
    assert ok, f"Unexpected errors: {errs}"


def test_schema_min_less_than_max():
    bad = {
        "extract_id": "x",
        "purpose": "treatment",
        "phi_mode": "expert",
        "schema": {"v": {"type": "number", "min": 10, "max": 5}},
    }
    ok, errs, _ = validate_manifest_text(json.dumps(bad))
    assert (not ok) and any("min >= max" in e for e in errs)
