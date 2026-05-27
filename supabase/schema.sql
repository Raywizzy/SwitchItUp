create table if not exists public.switchitup_state (
  id text primary key,
  state jsonb not null,
  updated_at timestamptz not null default now()
);

alter table public.switchitup_state enable row level security;

comment on table public.switchitup_state is
  'Single-row persistent state store for the Switch It Up MVP backend.';

