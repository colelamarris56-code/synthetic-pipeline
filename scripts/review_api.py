from __future__ import annotations
import os, psycopg, uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

DSN = os.getenv("PG_DSN")
app = FastAPI(title="Review Queue")


class ReviewIn(BaseModel):
    job_id: str
    title: str
    explain: str
    proposed_fix: dict | None = None
    risk: str


@app.post("/review/add")
def add(r: ReviewIn):
    with psycopg.connect(DSN) as con, con.cursor() as cur:
        cur.execute(
            """insert into review_item(job_id,title,explain,proposed_fix,risk)
               values(%s,%s,%s,%s,%s) returning review_id""",
            (r.job_id, r.title, r.explain, r.proposed_fix, r.risk),
        )
        rid = cur.fetchone()[0]
        con.commit()
        return {"review_id": rid}


@app.post("/review/decide/{rid}/{decision}")
def decide(rid: int, decision: str):
    assert decision in ("accepted", "rejected")
    with psycopg.connect(DSN) as con, con.cursor() as cur:
        cur.execute("update review_item set status=%s, decided_at=now() where review_id=%s",
                    (decision, rid))
        con.commit()
        return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8891)
