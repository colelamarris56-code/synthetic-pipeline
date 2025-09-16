create table if not exists review_item (
  review_id bigserial primary key,
  job_id text not null,
  title text not null,
  explain text not null,
  proposed_fix jsonb,
  risk text not null,
  status text not null default 'open',
  created_at timestamptz default now(),
  decided_at timestamptz
);
