# Changelog

## v1.7.5.1 — Correction du nom Superadmin
- Corrected the protected Superadmin username to the requested spelling `destrox` across the desktop UI, Python API, SQL protection, promotion template, and Edge Function.
- Updated the UI, Python API checks, Supabase role-protection migration, promotion SQL template, and `admin-users` Edge Function.
- No database records are migrated or deleted by this source correction.

# Changelog

## v1.7.5 — Superadmin système protégé
- Added the permanent `destrox` / `Superadmin` system identity.
- Administrators cannot edit or delete the protected Superadmin account.
- A database trigger blocks deletion of the Superadmin profile and changes to its username/role, including Auth user deletion cascading to profiles.
- Added Superadmin access to user administration and activity logs.
- Superadmin can manage ordinary accounts and Administrators, including removing the last Administrator, but cannot delete itself or create another Superadmin through the app.
- Added SQL to enable the role and a separate email-based profile promotion template.


## v1.7.4 — Journaux d'activité
- Added a French **Journaux d’activité** page, visible only to Administrateur.
- Added central audit events for successful login and logout via a Supabase Edge Function.
- Added database triggers to record insert/update/delete on sales, deposits and company expenses, with actor, timestamp and before/after snapshots.
- Expanded user management audit entries through `admin-users`.
- Added audit search and event-type filters.
- Prevented passwords from being stored in local SQLite audit event details.
- Kept current GPS/Starlink forms, PDF reports, cloud login and user roles.

## v1.7.3.2
- PDF export is written directly to the Windows Downloads folder with exact path confirmation.
