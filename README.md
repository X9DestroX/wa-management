## Version 1.7.4 — Journaux d’activité

- Nouveau menu **Journaux d’activité**, réservé à l’Administrateur.
- Trace les connexions réussies/déconnexions et chaque ajout, modification ou suppression de vente, dépôt, dépense et compte utilisateur.
- Les événements métiers sont enregistrés par des déclencheurs PostgreSQL dans Supabase avec l’auteur, l’horodatage, l’élément concerné et les données avant/après.
- Recherche dans les journaux et filtre par type d’événement.
- Les mots de passe ne sont jamais consignés dans les détails d’audit.
- **Migration obligatoire avant usage** : exécuter `supabase/migrations/0004_activity_audit.sql`, déployer la fonction Edge `auth-event`, puis mettre à jour la fonction `admin-users` à partir du code fourni.
- Guide détaillé : `ACTIVITY_LOGS_SETUP_FR.md`.

## Version 1.7.3.2 — Emplacement d’export PDF corrigé

L’export PDF est maintenant enregistré directement dans le dossier **Téléchargements Windows** du PC qui génère le rapport. Après l’export, une boîte de dialogue affiche le nom du fichier et son chemin complet. Cela évite que le téléchargement créé par le navigateur intégré (pywebview) soit difficile à retrouver.

Le dossier Windows Téléchargements configuré par l’utilisateur est respecté, y compris s’il est redirigé.

## Version 1.7.3 — Rapports PDF et dépenses d’entreprise

- Nouveau menu **Rapports** avec période hebdomadaire (du lundi au dimanche) ou mensuelle (mois civil).
- Export PDF multipage comprenant la synthèse des ventes GPS/Starlink, chiffre d’affaires, abonnements, dépôts financiers, dépenses d’entreprise, dépenses historiques associées aux ventes et position opérationnelle.
- Nouveau registre des dépenses d’entreprise dans **Finance / Dépôts** : montant, date, catégorie, mode de paiement, bénéficiaire, référence et notes, avec modification/suppression.
- Le tableau de bord tient compte des nouvelles dépenses d’entreprise.
- **Migration obligatoire avant usage** : exécuter `supabase/migrations/0002_company_expenses.sql` dans le SQL Editor de Supabase.
- Export PDF généré sur le PC à partir des données déjà récupérées avec la session employé; aucune clé secrète n’est ajoutée au desktop.

## Version 1.7.2 — Registre Starlink simplifié

Le registre complet des ventes est maintenant séparé en deux sections : les ventes GPS conservent leurs colonnes détaillées, tandis que les ventes Starlink affichent uniquement **Type d’appareil**, **Montant à payer**, **Date et heure** et **Note**, avec la colonne **Actions** pour Modifier/Supprimer.

# W-A Systeme de Gestion — v1.7.1 (Cloud initial)

## État de cette version

Cette version introduit un **mode Cloud Supabase optionnel**. La connexion Cloud utilise Supabase Auth (e-mail/mot de passe) et les données sont lues/écrites dans PostgreSQL via l'API Supabase. Chaque PC lance son interface locale sur `127.0.0.1`; aucun laptop n'a besoin de rester allumé comme serveur LAN lorsque le mode Cloud est configuré.

**Important : cette intégration initiale doit être testée avant usage quotidien.** Elle ne migre pas automatiquement les anciennes données SQLite. Gardez l'ancienne installation LAN disponible jusqu'à ce que l'import et les tests soient validés.

## Fonctionnalités conservées

- Interface entièrement en français et thème clair.
- GPS : nom du client, téléphone, numéro SIM, type Moto/Voiture/Camion, adresse, montant saisi manuellement, SIM + activation à 3 000 FCFA (inclut le premier mois), abonnements supplémentaires à 3 000 FCFA/mois, date/heure, abonnement effectué, note.
- Calcul GPS : `Total à payer = Montant + 3 000 + (Nombre d’abonnements supplémentaires × 3 000)`.
- Starlink : uniquement Type d’appareil, Montant à payer, Date et heure, Note.
- Ventes et dépôts : ajout, modification et suppression.
- Rôles : RH, Gestionnaire, Administrateur.
- Gestion des comptes centralisée via la fonction Edge `admin-users` en mode Cloud.
- Le mode LAN/SQLite reste disponible si aucun fichier de configuration Cloud n'est présent.

## Pré-requis Cloud

1. Le schéma `supabase/migrations/0001_initial_schema.sql` a été appliqué au projet.
2. La fonction `supabase/functions/admin-users/index.ts` a été déployée sous le nom `admin-users`.
3. Le compte `admin@wasystem.com` existe dans Supabase Auth et son profil a le rôle `Administrateur`.
4. Les employés ont chacun un compte Auth/profil et un mot de passe valide.
5. Les inscriptions publiques restent désactivées.

## Configurer un PC de test

1. Exécutez `build_exe.bat` sur le PC de développement avec **Python 3.12 x64**.
2. Copiez le dossier complet `dist/W-A Systeme de Gestion` sur un seul PC de test.
3. Lancez `configure_cloud.bat`.
4. Entrez l'URL du projet Supabase (par exemple `https://<project-ref>.supabase.co`) et la clé **Publishable** ou l'ancienne clé **anon** depuis les paramètres API du projet.
5. Ne saisissez jamais une clé `Secret` / `service_role`.
6. Lancez `W-A Systeme de Gestion.exe`.
7. Le statut devrait afficher **Cloud connecté**. Connectez-vous avec l'adresse e-mail Supabase et le mot de passe d'un compte existant.

Chaque PC doit effectuer cette configuration, car `cloud_config.json` est stocké dans le profil Windows de chaque utilisateur à `%USERPROFILE%\WA_Manager_System\cloud_config.json`.

## Sécurité

- La clé Publishable/anon peut être intégrée côté client si les politiques Row Level Security (RLS) sont appliquées.
- La clé Secret/service-role ne doit jamais être dans le desktop, le dépôt GitHub, une capture d'écran ou un fichier de configuration client.
- La fonction `admin-users` vérifie le rôle Administrateur côté serveur avant toute gestion des comptes.
- Les policies RLS limitent l'accès aux utilisateurs authentifiés. Ne réactivez pas les inscriptions publiques sans une nouvelle revue des permissions.

## Migration des données historiques

Le mode Cloud démarre sur les tables Supabase; il ne copie pas automatiquement le fichier local `%USERPROFILE%\WA_Manager_System\wa_manager.db`. Ne supprimez pas cette base. La prochaine étape est de préparer un import contrôlé SQLite → Supabase, puis de rapprocher les nombres de ventes/dépôts et les montants avant le basculement définitif.

## Build Windows

```bat
build_exe.bat
```

Le build crée `dist/W-A Systeme de Gestion/W-A Systeme de Gestion.exe`. Distribuez le dossier complet (pas seulement l'EXE) aux PC. Les clients n'ont pas à exécuter `build_exe.bat`.

## Hotfix v1.7.1
Fixed a missing `re` import that caused the error `name 're' is not defined` when attempting cloud save/edit/delete operations. Rebuild the executable from this source; the existing cloud configuration remains in `%USERPROFILE%\WA_Manager_System\cloud_config.json`.


## v1.7.5.1 — Correction du nom Superadmin

Le nom exact du compte système est `destrox`. Appliquez `supabase/migrations/0005_superadmin_protection.sql`, puis `supabase/migrations/PROMOTE_DESTROX_TEMPLATE.sql`, redéployez `supabase/functions/admin-users/index.ts` et reconstruisez l’application. Voir `SUPERADMIN_SETUP_FR.md`.

## v1.7.5 — Superadmin système

Voir `SUPERADMIN_SETUP_FR.md` pour ajouter le rôle `Superadmin`, déployer la fonction `admin-users` mise à jour, créer le compte Auth `destrox`, puis le promouvoir avec `supabase/migrations/PROMOTE_DESTROX_TEMPLATE.sql`. Le compte `destrox` ne peut pas être supprimé via l’application et ses identifiants/role sont protégés.
