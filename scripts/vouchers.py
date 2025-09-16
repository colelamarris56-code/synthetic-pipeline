from __future__ import annotations
import argparse, os, psycopg, hmac, hashlib, base64
from datetime import datetime, timedelta

SECRET = os.getenv("VOUCHER_SECRET", "change-me").encode()
DSN = os.getenv("PG_DSN", "postgresql://clinic:clinic_pw@127.0.0.1:5432/clinic")


def _hash(code: str) -> bytes:
    return hmac.new(SECRET, code.encode(), hashlib.sha256).digest()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", type=int, required=True)
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()

    code = base64.urlsafe_b64encode(os.urandom(18)).decode().rstrip("=")
    with psycopg.connect(DSN) as con, con.cursor() as cur:
        cur.execute(
            "insert into voucher(code_hash, tokens, expires_at) values (%s,%s,%s)",
            (_hash(code), args.tokens, datetime.utcnow() + timedelta(days=args.days)),
        )
        con.commit()
    print(f"Voucher code (share with client): {code} ({args.tokens} tokens, {args.days} days)")
