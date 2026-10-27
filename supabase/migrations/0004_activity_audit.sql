-- W-A Systeme de Gestion v1.7.4 — activity audit log
-- Run this once in Supabase SQL Editor before using the new audit page.
-- Preserves existing audit rows and business data.

alter table public.audit add column if not exists actor_id uuid references auth.users(id) on delete set null;
alter table public.audit add column if not exists actor_email text;
alter table public.audit add column if not exists actor_role text;
alter table public.audit add column if not exists entity_table text;
alter table public.audit add column if not exists entity_id text;
alter table public.audit add column if not exists operation text;
alter table public.audit add column if not exists before_data jsonb;
alter table public.audit add column if not exists after_data jsonb;
alter table public.audit add column if not exists auth_session_id text;

create index if not exists audit_created_at_desc_idx on public.audit (created_at desc);
create index if not exists audit_actor_id_created_at_idx on public.audit (actor_id, created_at desc);
create index if not exists audit_entity_created_at_idx on public.audit (entity_table, entity_id, created_at desc);
create unique index if not exists audit_auth_session_operation_uidx
  on public.audit (auth_session_id, operation)
  where auth_session_id is not null and operation in ('LOGIN','LOGOUT');

alter table public.audit enable row level security;
drop policy if exists "audit_admin_read" on public.audit;
create policy "audit_admin_read"
  on public.audit for select to authenticated
  using (public.current_app_role() = 'Administrateur');

-- Ordinary employees cannot forge, edit or delete audit rows through the public REST API.
revoke insert, update, delete, truncate, references, trigger on public.audit from anon, authenticated;
grant select on public.audit to authenticated;

create or replace function public.log_business_activity()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_actor_id uuid;
  v_actor_email text;
  v_actor_username text;
  v_actor_role text;
  v_record_id text;
  v_before jsonb;
  v_after jsonb;
  v_operation text;
  v_action text;
begin
  v_actor_id := auth.uid();
  v_actor_email := nullif(auth.jwt() ->> 'email', '');
  if v_actor_id is not null then
    select p.username, p.role into v_actor_username, v_actor_role
      from public.profiles p where p.id = v_actor_id;
  end if;

  if tg_op = 'INSERT' then
    v_after := to_jsonb(new);
    v_record_id := v_after ->> 'id';
  elsif tg_op = 'UPDATE' then
    v_before := to_jsonb(old);
    v_after := to_jsonb(new);
    v_record_id := coalesce(v_after ->> 'id', v_before ->> 'id');
  else
    v_before := to_jsonb(old);
    v_record_id := v_before ->> 'id';
  end if;

  v_operation := tg_op;
  v_action := case tg_op
    when 'INSERT' then 'Ajout'
    when 'UPDATE' then 'Modification'
    when 'DELETE' then 'Suppression'
    else tg_op
  end || ' : ' || case tg_table_name
    when 'sales' then 'vente'
    when 'deposits' then 'dépôt'
    when 'expenses' then 'dépense'
    else tg_table_name
  end;

  insert into public.audit (
    username, action, details, created_at, actor_id, actor_email, actor_role,
    entity_table, entity_id, operation, before_data, after_data
  ) values (
    coalesce(v_actor_username, v_actor_email, 'Utilisateur inconnu'),
    v_action,
    jsonb_build_object('source', 'database_trigger', 'table', tg_table_name,
                       'operation', tg_op, 'record_id', v_record_id),
    now(), v_actor_id, v_actor_email, v_actor_role,
    tg_table_name, v_record_id, v_operation, v_before, v_after
  );

  if tg_op = 'DELETE' then return old; end if;
  return new;
end;
$$;

revoke all on function public.log_business_activity() from public;

drop trigger if exists audit_sales_changes on public.sales;
create trigger audit_sales_changes
after insert or update or delete on public.sales
for each row execute function public.log_business_activity();

drop trigger if exists audit_deposit_changes on public.deposits;
create trigger audit_deposit_changes
after insert or update or delete on public.deposits
for each row execute function public.log_business_activity();

drop trigger if exists audit_expense_changes on public.expenses;
create trigger audit_expense_changes
after insert or update or delete on public.expenses
for each row execute function public.log_business_activity();
