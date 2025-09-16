create table if not exists account (
  account_id uuid primary key default gen_random_uuid(),
  name text not null,
  email text unique not null,
  status text not null default 'active'
);

create table if not exists api_key (
  key_id uuid primary key default gen_random_uuid(),
  account_id uuid references account(account_id),
  key_public text unique not null,
  key_hash bytea not null,
  created_at timestamptz default now(),
  status text not null default 'active'
);

create table if not exists credit_wallet (
  account_id uuid primary key references account(account_id),
  balance_tokens bigint not null default 0,
  updated_at timestamptz default now()
);

create table if not exists credit_ledger (
  entry_id bigserial primary key,
  account_id uuid references account(account_id),
  delta_tokens bigint not null,
  reason text not null,
  ref_id text,
  ts timestamptz default now()
);

create table if not exists payment (
  payment_id uuid primary key default gen_random_uuid(),
  account_id uuid references account(account_id),
  provider text not null,
  provider_ref text,
  status text not null,
  amount_cents int not null,
  purchased_tokens bigint not null,
  ts timestamptz default now()
);

create table if not exists voucher (
  code_hash bytea primary key,
  tokens bigint not null,
  expires_at timestamptz,
  redeemed_by uuid references account(account_id),
  redeemed_at timestamptz
);
