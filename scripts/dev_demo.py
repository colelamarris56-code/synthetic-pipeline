from __future__ import annotations
import os, uuid, sys
from pathlib import Path

# Ensure the project root (one level above "scripts") is on sys.path so local "src" can be imported
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.common.billing import debit_for_synth
from src.agents.envelope import run_agent

ACCOUNT = os.getenv("SP_ACCOUNT_ID", "00000000-0000-0000-0000-000000000001")


def qa_model(records):
    """Demo QA agent: returns ok for all, extend with real checks."""
    return {"summary": "ok", "flags": [], "confidence": 0.95}


def run_demo(export_dir: Path) -> Path:
    job_id = f"job:{uuid.uuid4()}"
    synth_records = [
        {"patient_id": "p1", "loinc": "4548-4", "unit_norm": "%", "value_norm": 6.5}
    ]

    qa = run_agent(
        agent="qa",
        task="validate_units",
        purpose="operations",
        phi_mode="safe_harbor",
        account_id=ACCOUNT,
        input_ref=f"extract://t2d_care_gaps_v3/{job_id}",
        records=synth_records,
        manifest_path="configs/manifests/t2d_care_gaps_v3.json",
        llm_call=qa_model,
        model_name="local-qa",
    )

    rows = len(synth_records)
    debit_for_synth(ACCOUNT, job_id, rows=rows, agent_calls=1, dp_training=False)

    export_dir.mkdir(parents=True, exist_ok=True)
    out = export_dir / "demo_records.jsonl"
    out.write_text("\n".join([str(r) for r in synth_records]))
    print(f"Wrote: {out}")
    return out


if __name__ == "__main__":
    base = Path(os.getenv("SP_EXPORT_DIR", "artifacts/exports"))
    run_demo(base)
