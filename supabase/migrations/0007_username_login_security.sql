-- W-A Systeme de Gestion v1.7.9
-- Username sign-in attempt protection: max 8 tries per username in a 15-minute window.
-- Only a trusted Edge Function using the service-role key may call these objects.

create table if not exists public.username_login_attempts (
  identifier_hash text primary key check (identifier_hash ~ '^[0-9a-f]{64}$'),
  attempts integer not null default 0 check (attempts >= 0),
  window_started_at timestamptz not null default now(),
  blocked_until timestamptz,
  updated_at timestamptz not null default now()
);

alter table public.username_login_attempts enable row level security;
revoke all on table public.username_login_attempts from public, anon, authenticated;
grant all on table public.username_login_attempts to service_role;

create or replace function public.consume_username_login_attempt(p_identifier_hash text)
returns table(allowed boolean, retry_after_seconds integer)
language plpgsql
security definer
set search_path = public
as $$
declare
  current_attempts integer;
  current_window timestamptz;
  current_blocked timestamptz;
  current_time timestamptz := clock_timestamp();
begin
  if p_identifier_hash is null or p_identifier_hash !~ '^[0-9a-f]{64}$' then
    raise exception 'Invalid login identifier hash';
  end if;

  insert into public.username_login_attempts(identifier_hash)
  values (p_identifier_hash)
  on conflict (identifier_hash) do nothing;

  select attempts, window_started_at, blocked_until
    into current_attempts, current_window, current_blocked
    from public.username_login_attempts
   where identifier_hash = p_identifier_hash
   for update;

  if current_blocked is not null and current_blocked > current_time then
    return query select false,
      greatest(1, ceil(extract(epoch from (current_blocked - current_time)))::integer);
    return;
  end if;

  if current_window < current_time - interval '15 minutes'
     or (current_blocked is not null and current_blocked <= current_time) then
    update public.username_login_attempts
       set attempts = 1,
           window_started_at = current_time,
           blocked_until = null,
           updated_at = current_time
     where identifier_hash = p_identifier_hash;
    return query select true, 0;
    return;
  end if;

  if current_attempts >= 8 then
    update public.username_login_attempts
       set blocked_until = current_time + interval '15 minutes',
           updated_at = current_time
     where identifier_hash = p_identifier_hash;
    return query select false, 900;
    return;
  end if;

  update public.username_login_attempts
     set attempts = current_attempts + 1,
         updated_at = current_time
   where identifier_hash = p_identifier_hash;

  return query select true, 0;
end;
$$;

create or replace function public.reset_username_login_attempts(p_identifier_hash text)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if p_identifier_hash is null or p_identifier_hash !~ '^[0-9a-f]{64}$' then
    raise exception 'Invalid login identifier hash';
  end if;
  delete from public.username_login_attempts
   where identifier_hash = p_identifier_hash;
end;
$$;

revoke all on function public.consume_username_login_attempt(text) from public, anon, authenticated;
revoke all on function public.reset_username_login_attempts(text) from public, anon, authenticated;
grant execute on function public.consume_username_login_attempt(text) to service_role;
grant execute on function public.reset_username_login_attempts(text) to service_role;
