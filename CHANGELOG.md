# CHANGELOG

## 1.7.1 — Cloud CRUD hotfix
- Fixed missing Python `re` import used by cloud API route matching.
- Restores the cloud save/edit/delete routing paths for sales, deposits, and administrator-managed users.
- No database schema change; no reconfiguration or SQLite migration is required.

## 1.7.0 — Cloud mode initial
- Added optional Supabase Cloud mode using email/password Supabase Auth.
- Each desktop client serves its UI/API only on loopback; company data lives in Supabase.
- Added cloud reads/writes for sales and deposits with existing GPS pricing and Starlink fields.
- Routed employee management through the deployed `admin-users` Edge Function.
- Added `configure_cloud.bat` / `.ps1` to configure URL and publishable key per PC.
- Preserved existing LAN/SQLite mode if Cloud configuration is not present.
- Added Supabase schema migration and Edge Function source to the repository.

Important: This is an initial cloud integration release. Existing local SQLite records are not automatically imported; keep the existing LAN version available until migration and acceptance testing are complete.
