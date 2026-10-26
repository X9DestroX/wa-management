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
