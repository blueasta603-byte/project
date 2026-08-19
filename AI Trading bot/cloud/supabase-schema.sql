create table if not exists trades (
  id text primary key,
  symbol text not null,
  side text not null,
  setup text,
  timeframe text,
  entry_price text,
  exit_price text,
  stop_loss text,
  take_profit text,
  size text,
  opened_at text,
  closed_at text,
  session text,
  pnl_usd text,
  pnl_r text,
  grade text,
  tags jsonb,
  notes text,
  created_at text not null
);

create table if not exists reflections (
  id bigint generated always as identity primary key,
  created_at text not null,
  content text not null
);
