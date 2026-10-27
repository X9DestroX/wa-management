-- Run only AFTER creating the desired Auth user in Supabase Dashboard → Authentication → Users.
-- Replace destrox@superadmin.com with the exact email you selected for destrox.
-- This changes the profile only; it does not create or expose the password.
do $$
declare
  target_email text := lower('destrox@superadmin.com');
  target_id uuid;
begin
  if target_email = 'destrox@superadmin.com' or target_email not like '%@%' then
    raise exception 'Replace destrox@superadmin.com with destrox account email before running this SQL.';
  end if;

  select id into target_id from auth.users where lower(email) = target_email;
  if target_id is null then
    raise exception 'No Supabase Auth user found for the supplied email. Create the user first.';
  end if;

  if exists (select 1 from public.profiles where lower(username) = 'destrox' and id <> target_id) then
    raise exception 'Username destrox is already assigned to a different profile. Resolve that profile first.';
  end if;

  update public.profiles
     set username = 'destrox',
         full_name = coalesce(nullif(trim(full_name), ''), 'Destrox'),
         role = 'Superadmin'
   where id = target_id;

  if not found then
    raise exception 'Supabase Auth user exists but has no public.profiles row. Check the auth-user trigger.';
  end if;
end $$;

select p.username, p.full_name, p.role, u.email
from public.profiles p
join auth.users u on u.id = p.id
where p.username = 'destrox';
