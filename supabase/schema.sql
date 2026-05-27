create table if not exists public.switchitup_state (
  id text primary key,
  state jsonb not null,
  updated_at timestamptz not null default now()
);

alter table public.switchitup_state enable row level security;

comment on table public.switchitup_state is
  'Single-row persistent state store for the Switch It Up MVP backend.';

grant select, insert, update on public.switchitup_state to anon;

drop policy if exists "switchitup_mvp_select" on public.switchitup_state;
drop policy if exists "switchitup_mvp_insert" on public.switchitup_state;
drop policy if exists "switchitup_mvp_update" on public.switchitup_state;

create policy "switchitup_mvp_select"
  on public.switchitup_state
  for select
  to anon
  using (id = 'production');

create policy "switchitup_mvp_insert"
  on public.switchitup_state
  for insert
  to anon
  with check (id = 'production');

create policy "switchitup_mvp_update"
  on public.switchitup_state
  for update
  to anon
  using (id = 'production')
  with check (id = 'production');
