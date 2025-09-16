from __future__ import annotations
import os, psycopg

DSN = os.getenv("PG_DSN", "postgresql://clinic:clinic_pw@127.0.0.1:5432/clinic")


def log_agent(account_id: str, agent: str, task: str, *, input_ref: str,
              purpose: str, phi_mode: str, rows: int, prompt_hash: str,
              model: str) -> None:
    with psycopg.connect(DSN) as con, con.cursor() as cur:
        cur.execute(
            """
            insert into agent_audit(account_id,agent,task,input_ref,purpose,phi_mode,rows,prompt_hash,model)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (account_id, agent, task, input_ref, purpose, phi_mode, rows, prompt_hash, model),
        )
        con.commit()
