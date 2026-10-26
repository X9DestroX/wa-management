# Cloud database migration — important status

This package includes the Starlink form update, but it is **not yet connected to Supabase**.
The current runtime still uses the local SQLite database and LAN server. Do not assume multiple laptops in different locations share data through the cloud yet.

## Recommended target

Use Supabase (managed PostgreSQL + Supabase Auth) rather than MQTT as the primary database. MQTT is messaging infrastructure, not a replacement for a relational database or employee authentication.

Before switching production data to cloud:
1. Create a Supabase project under the company's account.
2. Decide who will own billing and recovery access.
3. Configure employee authentication and roles (RH, Gestionnaire, Administrateur).
4. Create the sales, deposits, and audit tables with row-level security.
5. Build and test a migration/import from `wa_manager.db`.
6. Test two separate laptops using separate employee accounts.
7. Verify role enforcement, edits/deletes, backups, and recovery before moving daily operations.

**Never put a Supabase service-role key in the desktop application.** Desktop apps can be inspected. The client should use Supabase Auth and the publishable/anon key with strict Row Level Security, or go through a trusted backend service.

## Current Starlink form behavior

When Type d'appareil is GPS, the existing GPS form remains.
When Type d'appareil is Starlink, the form shows only:
- Type d'appareil
- Montant à payer

The same conditional behavior is applied in the edit-sale dialog. Existing historical Starlink data is not deleted.


## Step 5 — Cloud mode in v1.7.0

The optional cloud gateway is now included in `wa_manager.py`. It uses a per-laptop `cloud_config.json` stored in `%USERPROFILE%\\WA_Manager_System`; `configure_cloud.bat` creates it using the project URL and a publishable/anon key.

Cloud mode currently connects:
- Supabase Auth password login (email/password)
- `public.profiles` for profile/role lookup
- `public.sales` and `public.deposits` for reads and writes
- Edge Function `admin-users` for administrator account management

**Important:** test on one non-production laptop first. This release does not automatically import the local SQLite DB. Verify sign-in, CRUD, roles, date/time handling, and user management before using it for live transactions. The existing SQLite/LAN database is preserved.
