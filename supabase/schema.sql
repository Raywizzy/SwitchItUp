create table if not exists public.switchitup_state (
  id text primary key,
  state jsonb not null,
  updated_at timestamptz not null default now()
);

alter table public.switchitup_state enable row level security;

comment on table public.switchitup_state is
  'Persistent JSONB state store for the Switch It Up MVP backend. The production row seeds the public demo; session_* rows isolate browser sessions until full auth lands.';

grant select, insert, update on public.switchitup_state to anon;

drop policy if exists "switchitup_mvp_select" on public.switchitup_state;
drop policy if exists "switchitup_mvp_insert" on public.switchitup_state;
drop policy if exists "switchitup_mvp_update" on public.switchitup_state;

create policy "switchitup_mvp_select"
  on public.switchitup_state
  for select
  to anon
  using (id = 'production' or id like 'session\_%' escape '\');

create policy "switchitup_mvp_insert"
  on public.switchitup_state
  for insert
  to anon
  with check (id = 'production' or id like 'session\_%' escape '\');

create policy "switchitup_mvp_update"
  on public.switchitup_state
  for update
  to anon
  using (id = 'production' or id like 'session\_%' escape '\')
  with check (id = 'production' or id like 'session\_%' escape '\');
