from __future__ import annotations
from typing import Literal
from .billing import apply_ledger, BillingEvent, _pg

Provider = Literal["paypal", "square", "dwolla", "invoice", "btcpay"]


def record_payment(account_id: str, provider: Provider, provider_ref: str,
                   amount_cents: int, purchased_tokens: int, status: str = "paid"):
    with _pg() as con, con.cursor() as cur:
        cur.execute(
            """
            insert into payment(account_id, provider, provider_ref, status, amount_cents, purchased_tokens)
            values (%s,%s,%s,%s,%s,%s)
            """,
            (account_id, provider, provider_ref, status, amount_cents, purchased_tokens),
        )
        con.commit()
    if status == "paid":
        apply_ledger(BillingEvent(account_id, purchased_tokens, reason="purchase",
                                  ref_id=f"{provider}:{provider_ref}"))

# Webhook shims (validate upstream in your reverse proxy)

def paypal_capture_webhook(payload: dict):
    order_id = payload["resource"]["id"]
    amount_cents = int(float(payload["resource"]["purchase_units"][0]["amount"]["value"]) * 100)
    account_id = payload["resource"].get("custom_id")
    purchased_tokens = amount_cents // 5
    record_payment(account_id, "paypal", order_id, amount_cents, purchased_tokens, status="paid")


def square_invoice_webhook(payload: dict):
    invoice_id = payload["data"]["id"]
    amount_cents = int(payload["data"]["object"]["invoice"]["payment_requests"][0]["total_amount_money"]["amount"])
    account_id = payload["data"]["object"]["invoice"]["primary_recipient"]["customer_id"]
    purchased_tokens = amount_cents // 5
    record_payment(account_id, "square", invoice_id, amount_cents, purchased_tokens, status="paid")


def mark_invoice_paid(account_id: str, invoice_no: str, amount_cents: int, purchased_tokens: int):
    record_payment(account_id, "invoice", invoice_no, amount_cents, purchased_tokens, status="paid")


def btcpay_webhook(payload: dict):
    inv_id = payload["invoiceId"]
    amount_cents = int(float(payload["amountPaid"]) * 100)
    account_id = payload["metadata"].get("posData")
    purchased_tokens = amount_cents // 5
    record_payment(account_id, "btcpay", inv_id, amount_cents, purchased_tokens, status="paid")
