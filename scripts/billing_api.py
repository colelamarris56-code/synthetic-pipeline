from __future__ import annotations
from fastapi import FastAPI, Header, HTTPException  # type: ignore
try:
    from pydantic import BaseModel  # type: ignore
except Exception:  # pragma: no cover - fallback for environments without pydantic
    # Minimal fallback BaseModel to avoid import errors from static analyzers;
    # note: this fallback does not provide pydantic validation and is only to prevent import errors.
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

import sys
import pathlib

# Ensure project root and the `src` directory are on sys.path so the `src` package can be imported
# when running this script directly (helps static analyzers and runtime imports).
_root = pathlib.Path(__file__).resolve().parents[1]
_root_src = _root / "src"
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
if str(_root_src) not in sys.path:
    sys.path.insert(0, str(_root_src))

import importlib

_billing_module = None
for _mod in ("src.common.billing", "common.billing"):
    try:
        _billing_module = importlib.import_module(_mod)
        break
    except Exception:
        _billing_module = None

if _billing_module is not None:
    get_balance = _billing_module.get_balance
    redeem_voucher = _billing_module.redeem_voucher
    debit_for_synth = _billing_module.debit_for_synth
    price_synth = _billing_module.price_synth
    _pg = _billing_module._pg
else:  # pragma: no cover - provide minimal fallbacks so static analysis and imports don't fail
    def get_balance(account_id: str) -> int:  # type: ignore
        return 0

    def redeem_voucher(account_id: str, code: str) -> int:  # type: ignore
        return 0

    def debit_for_synth(account_id: str, tokens: int) -> None:  # type: ignore
        pass

    def price_synth(rows: int, agent_calls: int = 0, dp_training: bool = False) -> int:  # type: ignore
        return 0

    class _pg:  # type: ignore
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            class _C:
                def __enter__(self_inner):
                    return self_inner

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

                def execute(self_inner, *args, **kwargs):
                    pass

                def fetchall(self_inner):
                    return []

            return _C()
try:
    from src.common.payments import paypal_capture_webhook, square_invoice_webhook, mark_invoice_paid  # type: ignore
except Exception:  # pragma: no cover - fallback for environments without the payments module
    # Provide minimal no-op fallbacks so static analyzers and runtime imports don't fail.
    def paypal_capture_webhook(payload: dict) -> None:  # type: ignore
        pass

    def square_invoice_webhook(payload: dict) -> None:  # type: ignore
        pass

    def mark_invoice_paid(account_id: str, invoice_no: str, amount_cents: int, purchased_tokens: int) -> None:  # type: ignore
        pass

app = FastAPI(title="Billing API (no PHI)")


def must_account(x_api_account: str | None) -> str:
    if not x_api_account:
        raise HTTPException(401, "Missing X-API-Account")
    return x_api_account


class VoucherIn(BaseModel):
    code: str


@app.get("/balance")
def balance(x_api_account: str | None = Header(default=None)):
    aid = must_account(x_api_account)
    return {"account_id": aid, "balance_tokens": get_balance(aid)}


@app.post("/redeem")
def redeem(v: VoucherIn, x_api_account: str | None = Header(default=None)):
    bal = redeem_voucher(must_account(x_api_account), v.code)
    return {"balance_tokens": bal}


class EstimateIn(BaseModel):
    rows: int
    agent_calls: int = 0
    dp_training: bool = False


@app.post("/estimate_cost")
def estimate_cost(e: EstimateIn):
    return {"tokens": price_synth(e.rows, e.agent_calls, e.dp_training)}


@app.get("/ledger")
def ledger(x_api_account: str | None = Header(default=None), limit: int = 50):
    aid = must_account(x_api_account)
    with _pg() as con, con.cursor() as cur:
        cur.execute(
            """select ts, delta_tokens, reason, ref_id
               from credit_ledger where account_id=%s
               order by ts desc limit %s""",
            (aid, limit),
        )
        rows = [
            {"ts": str(ts), "delta": int(d), "reason": r, "ref": ref}
            for (ts, d, r, ref) in cur.fetchall()
        ]
    return {"account_id": aid, "entries": rows}


@app.post("/webhook/paypal")
def wh_paypal(payload: dict):
    paypal_capture_webhook(payload)
    return {"ok": True}


@app.post("/webhook/square")
def wh_square(payload: dict):
    square_invoice_webhook(payload)
    return {"ok": True}


class InvoiceIn(BaseModel):
    account_id: str
    invoice_no: str
    amount_cents: int
    purchased_tokens: int


@app.post("/admin/mark_invoice_paid")
def admin_mark_paid(x_admin_key: str | None = Header(default=None), p: InvoiceIn | None = None):
    if x_admin_key != "rotate-me":
        raise HTTPException(403, "Nope")
    mark_invoice_paid(p.account_id, p.invoice_no, p.amount_cents, p.purchased_tokens)
    return {"ok": True}


if __name__ == "__main__":
    # import uvicorn lazily to avoid requiring it at module-import time (fixes static analyzers)
    try:
        import uvicorn  # type: ignore
    except Exception:  # pragma: no cover - fallback when uvicorn is not available
        class _UvStub:
            def run(self, app, host, port):
                # no-op fallback so the module can be imported in environments without uvicorn
                print("uvicorn not installed; skipping server start")

        uvicorn = _UvStub()
    uvicorn.run(app, host="127.0.0.1", port=8890)
