# v1.7.8 — Refonte visuelle professionnelle

- Palette claire modernisée : bleu marine, bleu de confiance et accents or discrets.
- Amélioration des cartes, tableaux, formulaires, boutons, fenêtres modales et navigation.
- États actifs, survol, focus clavier et styles responsive plus cohérents.
- Les changements sont limités à la présentation : aucune logique API, base de données, autorisation ou métier n'est modifiée.

# v1.7.7 — Scanner et import Excel/CSV

- Ajout du scan par caméra pour codes-barres et QR (API native + solution de secours).
- Ajout de l’import .xlsx et .csv avec aperçu, validation, détection des doublons et confirmation.
- Ajout du modèle CSV en français.
- Les quantités initiales importées alimentent l’historique de stock.

# Changelog

## v1.7.6 — Catalogue produits et stock
- Ajout du catalogue central Supabase avec les six champs métier : catégorie, nom du produit, code-barres/QR, prix de vente, quantité en stock et notes.
- Ajout de l’historique des mouvements : stock initial, ajustement, vente et retour en stock.
- Les nouvelles ventes exigent la sélection d’un produit du catalogue et sa quantité. Le prix est calculé depuis le prix catalogue.
- Les ventes réduisent le stock au sein d’une transaction PostgreSQL; les quantités insuffisantes sont refusées.
- La modification d’une vente ajuste le stock si le produit ou la quantité change; la suppression restitue le stock.
- Les produits sont archivés, pas physiquement supprimés, afin de préserver l’historique.
- Ajout du support de catalogue en mode SQLite local pour préserver le fonctionnement hors cloud.
- Le champ code-barres/QR est saisissable manuellement dans cette version. Import Excel et scan caméra mobile restent une étape suivante.

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
