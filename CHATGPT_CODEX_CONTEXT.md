# ChatGPT Codex Context (Repo Snapshot)
Purpose: Community Clinic EHR Extracts synthesizer with HIL review, token billing, and agent guardrails.

Authoritative code:
- src/common/{privacy.py,audit.py,billing.py,payments.py,manifest.py}
- src/agents/envelope.py
- scripts/{billing_api.py,review_api.py,dashboard_app.py,dev_demo.py,vouchers.py}
- configs/manifests/**, configs/{governance.yml,equity.yml,privacy.json,qa_flags.json,billing.json}
- db/{billing.sql,audit.sql,review.sql}

Non-authoritative (ignore unless asked): data/**, artifacts/**, docs/**
Style: Python 3.11, snake_case, 88-char lines, comments explain WHY.
Contracts: keep function signatures stable unless explicitly told.
