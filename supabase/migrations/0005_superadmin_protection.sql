-- W-A Systeme de Gestion v1.7.5 — protect the permanent system Superadmin.
-- Run this in Supabase SQL Editor before promoting the Auth user to Superadmin (user may be created before or after).
-- This file enables the role and installs database-level protection. It does not create credentials.

begin;

-- Add the fourth role while retaining the three employee roles.
alter table public.profiles drop constraint if exists profiles_role_check;
alter table public.profiles add constraint profiles_role_check
  check (role in ('RH', 'Gestionnaire', 'Administrateur', 'Superadmin'));

-- The audit log is visible to Administrateur and the system Superadmin.
drop policy if exists "audit_admin_read" on public.audit;
create policy "audit_admin_read"
  on public.audit for select to authenticated
  using (public.current_app_role() in ('Administrateur', 'Superadmin'));

-- Protect username destrox / role Superadmin even if a future application bug attempts to
-- update or delete the profile. Deleting the corresponding Auth user cascades to profiles;
-- this trigger rejects that cascade and rolls back the transaction.
create or replace function public.protect_system_superadmin_profile()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if tg_op = 'DELETE' then
    if lower(coalesce(old.username, '')) = 'destrox' or old.role = 'Superadmin' then
      raise exception 'The system Superadmin account destrox is protected and cannot be deleted.';
    end if;
    return old;
  end if;

  if tg_op = 'UPDATE' then
    if lower(coalesce(old.username, '')) = 'destrox' or old.role = 'Superadmin' then
      if lower(coalesce(new.username, '')) <> 'destrox' or new.role <> 'Superadmin' then
        raise exception 'The system Superadmin username and role are protected.';
      end if;
    end if;
    return new;
  end if;
  return new;
end;
$$;

revoke all on function public.protect_system_superadmin_profile() from public, anon, authenticated;
drop trigger if exists protect_system_superadmin_profile on public.profiles;
create trigger protect_system_superadmin_profile
before update or delete on public.profiles
for each row execute function public.protect_system_superadmin_profile();

commit;
