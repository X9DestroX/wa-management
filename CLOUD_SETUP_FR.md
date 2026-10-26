# Configuration cloud — W-A Systeme de Gestion v1.7.1

## Ce que cette version fait
- Mode Cloud optionnel : chaque laptop sert l'interface uniquement sur `127.0.0.1` et communique avec Supabase.
- Connexion par e-mail/mot de passe Supabase Auth.
- Les ventes et dépôts sont lus/modifiés dans les tables Supabase.
- Les fonctions d'administration des comptes passent par la Edge Function `admin-users`.
- Le mode LAN/SQLite reste disponible tant que `cloud_config.json` n'est pas configuré.

## Pré-requis de cloud
- Migration SQL Step 1 appliquée.
- Comptes Supabase Auth et profils créés.
- Fonction Edge `admin-users` déployée.
- Dans `public.profiles`, `admin@wasystem.com` doit avoir `role='Administrateur'`.
- La configuration du premier compte doit être vérifiée avant la migration des données.

## Configuration de test (un PC à la fois)
1. Ne désinstallez pas et ne remplacez pas votre version opérationnelle actuelle.
2. Décompressez la nouvelle source et générez l'exécutable avec `build_exe.bat` sur le PC de développement.
3. Copiez le dossier `dist/W-A Systeme de Gestion` sur un seul PC de test.
4. Lancez `configure_cloud.bat`.
5. Saisissez l'URL du projet Supabase et la **clé Publishable** depuis Project Settings → API Keys. La clé commence généralement par `sb_publishable_`. Une ancienne clé `anon` est aussi utilisable.
6. Ne saisissez jamais la clé `secret` / `service_role`. Elle ne doit pas être dans l'application desktop.
7. Lancez `W-A Systeme de Gestion.exe`. Le statut devrait afficher `Cloud connecté`.
8. Connectez-vous avec l'adresse e-mail et le mot de passe d'un utilisateur Supabase existant.

## Données existantes
Cette étape ne migre pas les anciennes données du fichier SQLite. La base locale n'est ni supprimée ni écrasée. Gardez la version LAN existante comme version opérationnelle jusqu'à ce que l'import SQLite → Supabase et les tests de rapprochement soient terminés.

## Notes
- Internet est nécessaire pour le mode Cloud.
- Chaque laptop doit exécuter une version contenant le support Cloud et disposer de son propre fichier de configuration dans `%USERPROFILE%\WA_Manager_System\cloud_config.json`.
- Les comptes sont gérés via `admin-users`, jamais par clé secret côté desktop.
- Les tables `sales` et `deposits` doivent avoir les policies RLS créées à Step 1.
