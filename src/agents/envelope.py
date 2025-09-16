from __future__ import annotations
import json, os, hashlib
from typing import List, Dict, Callable
from src.common.privacy import deidentify
from src.common.audit import log_agent

DEFAULTS = json.loads(open("configs/manifests/_defaults.json").read())


def _hash_prompt(prompt: str) -> str:
    return "sha256:" + hashlib.sha256(prompt.encode()).hexdigest()


def run_agent(
    *,
    agent: str,
    task: str,
    purpose: str,
    phi_mode: str,
    account_id: str,
    input_ref: str,
    records: List[Dict],
    manifest_path: str,
    llm_call: Callable[[List[Dict]], Dict],
    model_name: str = "local-llm",
) -> Dict:
    mf = json.loads(open(manifest_path).read())
    cap = min(mf.get("agent_record_cap", DEFAULTS["agent_record_cap"]), len(records))
    payload = deidentify(records[:cap], mode=phi_mode)

    prompt_hash = _hash_prompt(f"{agent}:{task}:{manifest_path}:{purpose}:{phi_mode}")
    result = llm_call(payload)

    log_agent(
        account_id,
        agent,
        task,
        input_ref=input_ref,
        purpose=purpose,
        phi_mode=phi_mode,
        rows=len(payload),
        prompt_hash=prompt_hash,
        model=model_name,
    )
    return {"agent": agent, "task": task, "result": result, "confidence": result.get("confidence", 0.0)}
