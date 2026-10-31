# Connexion avec nom d’utilisateur — v1.7.9.1 (correctif)

## Changements visibles
- Le texte d'exemple sous le champ de connexion a été supprimé.
- Le champ accepte un nom d'utilisateur enregistré ou une adresse e-mail.
- La connexion par e-mail continue d'utiliser directement Supabase Auth.
- La connexion par nom d'utilisateur passe par l'Edge Function sécurisée `username-login`.

## Pourquoi la connexion par nom d'utilisateur peut échouer
La fonction `username-login` doit être déployée dans Supabase et son contrôle **Verify JWT doit être désactivé pour cette fonction uniquement**, car l'utilisateur n'a pas encore de jeton de session avant la connexion. Le code de la fonction vérifie lui-même le nom d'utilisateur et le mot de passe via Supabase Auth.

## Vérification et déploiement requis
1. Dans Supabase → SQL Editor, vérifiez que `0007_username_login_security.sql` a déjà été exécuté. Ne l'exécutez pas à nouveau si la table `username_login_attempts` et les fonctions RPC existent.
2. Dans Supabase → Edge Functions, ouvrez `username-login`.
3. Remplacez son code par `supabase/functions/username-login/index.ts` de ce paquet, puis déployez.
4. Dans les détails de cette fonction, désactivez **Verify JWT**. Ne désactivez pas ce contrôle pour `admin-users`, `auth-event` ou d'autres fonctions.
5. Testez l'URL de la fonction par une requête GET. Elle doit renvoyer un JSON avec `ok: true`, `service: "username-login"`, `version: "1.7.9.1"`. Cela vérifie le déploiement et le réglage Verify JWT, mais ne teste pas encore les identifiants d'un employé.
6. Recréez l'exécutable avec `build_exe.bat` et testez un identifiant par nom d'utilisateur.

## Codes de diagnostic affichés par le correctif
- Fonction introuvable / HTTP 404 : déployer `username-login`.
- `Invalid JWT`, `Invalid Token` ou absence d'en-tête Authorization : vérifier que **Verify JWT** est désactivé pour `username-login` uniquement, puis redéployer.
- Service de connexion indisponible / HTTP 503 : vérifier la migration SQL `0007`, les variables d'environnement Supabase de l'Edge Function et le code déployé.
- Identifiant ou mot de passe incorrect : la fonction est joignable, mais Supabase Auth a refusé les identifiants ou le nom d'utilisateur ne correspond à aucun profil.

## Mots de passe
- Les nouveaux mots de passe des comptes RH, Gestionnaire et Administrateur créés/modifiés par la fonction `admin-users` doivent contenir 6 à 8 caractères. Les chiffres seuls sont acceptés si la politique Supabase le permet.
- Les mots de passe existants plus longs restent valides pour la connexion.
- Le Superadmin `destrox` conserve un minimum de 12 caractères lors d'un changement de mot de passe.
- Préférez 8 caractères plutôt que 6 pour les employés. Conservez pour `destrox` un mot de passe long et unique et activez la MFA si disponible.

## Configuration des clés dans l'Edge Function
La fonction prend en charge les variables Supabase intégrées `SUPABASE_PUBLISHABLE_KEYS` et `SUPABASE_SECRET_KEYS` ainsi que les variables historiques. Les nouvelles clés `sb_publishable_*` et `sb_secret_*` sont envoyées dans l'en-tête `apikey` uniquement. La clé secrète n'est jamais incluse dans le desktop ou le dépôt GitHub.

## Interface
Le texte « Exemple : admin, yassir, hr ou votre adresse e-mail professionnelle » a été retiré de l'écran de connexion.
