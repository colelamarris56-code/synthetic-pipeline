from __future__ import annotations
import hashlib, hmac, os, json
from dataclasses import dataclass
from typing import Optional
import psycopg

CONFIG = json.loads(open("configs/billing.json").read())
DSN = os.getenv("PG_DSN", "postgresql://clinic:clinic_pw@127.0.0.1:5432/clinic")


@dataclass
class BillingEvent:
    account_id: str
    tokens: int
    reason: str
    ref_id: str | None = None


def _pg():
    return psycopg.connect(DSN)


def get_balance(account_id: str) -> int:
    with _pg() as con, con.cursor() as cur:
        cur.execute("select balance_tokens from credit_wallet where account_id=%s", (account_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


def _upsert_wallet(cur, account_id: str):
    cur.execute(
        """
        insert into credit_wallet(account_id, balance_tokens)
        values (%s, 0)
        on conflict (account_id) do nothing
        """,
        (account_id,),
    )


def apply_ledger(evt: BillingEvent) -> int:
    with _pg() as con, con.cursor() as cur:
        _upsert_wallet(cur, evt.account_id)
        cur.execute(
            "insert into credit_ledger(account_id, delta_tokens, reason, ref_id) values (%s,%s,%s,%s)",
            (evt.account_id, evt.tokens, evt.reason, evt.ref_id),
        )
        cur.execute(
            "update credit_wallet set balance_tokens = balance_tokens + %s, updated_at=now() where account_id=%s returning balance_tokens",
            (evt.tokens, evt.account_id),
        )
        bal = cur.fetchone()[0]
        con.commit()
        return int(bal)


def price_synth(rows: int, agent_calls: int = 0, dp_training: bool = False) -> int:
    c = CONFIG["costs"]
    total = c["synth_job_base"] + rows * c["synth_row"] + agent_calls * c["agent_call"]
    if dp_training:
        total += c["dp_training_min"]
    return int(round(total))


def debit_for_synth(account_id: str, job_id: str, rows: int, agent_calls: int = 0,
                    dp_training: bool = False) -> int:
    cost = -price_synth(rows, agent_calls, dp_training)
    bal = get_balance(account_id)
    if bal + cost < 0:
        raise RuntimeError(f"Insufficient tokens: need {-cost}, have {bal}")
    return apply_ledger(BillingEvent(account_id, cost, reason="synthesis", ref_id=job_id))

# Vouchers
_SECRET = os.getenv("VOUCHER_SECRET", "change-me").encode()


def _hash_code(code: str) -> bytes:
    return hmac.new(_SECRET, code.encode(), hashlib.sha256).digest()


def redeem_voucher(account_id: str, code: str) -> int:
    h = _hash_code(code)
    with _pg() as con, con.cursor() as cur:
        cur.execute("select tokens, expires_at, redeemed_by from voucher where code_hash=%s", (h,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Invalid voucher")
        tokens, expires_at, redeemed_by = row
        if redeemed_by is not None:
            raise ValueError("Voucher already redeemed")
        if expires_at and hasattr(expires_at, "tzinfo") and expires_at.tzinfo and expires_at < psycopg.TimestampTz.now():
            raise ValueError("Voucher expired")
        cur.execute("update voucher set redeemed_by=%s, redeemed_at=now() where code_hash=%s", (account_id, h))
        apply_ledger(BillingEvent(account_id, int(tokens), reason="purchase", ref_id="voucher"))
        con.commit()
        return get_balance(account_id)
