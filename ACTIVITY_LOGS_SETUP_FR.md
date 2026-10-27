# W-A Systeme de Gestion v1.7.4 — Journaux d'activité

Cette version ajoute une page **Journaux d’activité** réservée au rôle **Administrateur**.

## Événements enregistrés
- Connexions réussies et déconnexions (via la fonction Edge `auth-event`).
- Ajout, modification et suppression des ventes GPS/Starlink.
- Ajout, modification et suppression des dépôts.
- Ajout, modification et suppression des dépenses d’entreprise.
- Création, modification et suppression des comptes utilisateurs (via la fonction Edge `admin-users`).
- Pour les modifications et suppressions des transactions, les états avant/après sont conservés pour expliquer ce qui a changé.

Les journaux sont lus par la page protégée `/api/audit`. Seul un compte dont le rôle cloud vaut `Administrateur` peut consulter les événements. Les employés authentifiés ne peuvent pas créer, modifier ou supprimer directement les lignes d’audit par l’API REST.

## Installation — faire ces étapes avant de tester la page

### 1. Appliquer une migration SQL
Dans Supabase → SQL Editor → New query, ouvrez/copiez `supabase/migrations/0004_activity_audit.sql` puis cliquez **Run**. Elle ajoute les colonnes d’audit, verrouille l’écriture directe dans `audit` et met en place les déclencheurs de base de données. Elle ne supprime aucune vente, aucun dépôt ni aucune dépense.

### 2. Déployer la fonction `auth-event`
Dans Supabase → Edge Functions → Deploy a new function → Via Editor :
1. Nom : `auth-event`
2. Copier le contenu de `supabase/functions/auth-event/index.ts`
3. Déployer.

La fonction utilise les secrets fournis par l’environnement Edge Functions de Supabase. N’ajoutez pas de clé secrète/service-role dans l’application Windows ou dans GitHub.

### 3. Mettre à jour `admin-users` (recommandé)
Ouvrez la fonction déjà existante `admin-users`, remplacez son code par `supabase/functions/admin-users/index.ts` de cette version, puis déployez-la. Cela rend les événements de gestion d’utilisateurs plus détaillés. Les anciennes entrées déjà enregistrées restent lisibles.

### 4. Construire l'application
Copier les fichiers source de cette version dans le dépôt local (garder `.git`), puis exécuter `build_exe.bat`. Configurer le cloud n'est pas nécessaire une seconde fois si le fichier de configuration existe déjà dans `%USERPROFILE%\WA_Manager_System\cloud_config.json`.

## Vérification recommandée
1. Se connecter avec l'administrateur. Ouvrir **Journaux d’activité** : une ligne **Connexion réussie** devrait apparaître (après le déploiement d'`auth-event`).
2. Ajouter une vente test, modifier son montant/note, puis la supprimer. Chaque action doit apparaître avec son auteur et l’horodatage.
3. Ajouter puis supprimer un dépôt/dépense de test.
4. Vérifier qu'un compte RH ou Gestionnaire ne voit pas la page Journaux d’activité. La vérification d'accès est également effectuée côté API et par RLS.

## Notes importantes
- La table d'audit contient des états avant/après de transactions; elle peut contenir des informations client. Son accès est réservé aux Administrateurs.
- Les mots de passe et les clés secrètes ne sont jamais ajoutés aux détails d'audit.
- Les journaux déjà présents dans la table `audit` sont conservés, même si leurs champs enrichis sont vides.
- Une tentative de connexion échouée n'est pas incluse dans cette version; seuls les événements de session authentifiée sont consignés, sans risque d'accepter des événements anonymes fabriqués.
