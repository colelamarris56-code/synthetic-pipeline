create table if not exists agent_audit (
  audit_id bigserial primary key,
  account_id uuid,
  agent text not null,
  task text not null,
  input_ref text,
  purpose text not null,
  phi_mode text not null,
  rows int not null,
  prompt_hash text,
  model text,
  ts timestamptz default now()
);
