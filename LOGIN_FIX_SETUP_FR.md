# Correctif de connexion v1.7.9.1 — guide de mise à jour

Ce correctif retire le texte d'exemple du formulaire de connexion et fiabilise la connexion par nom d'utilisateur avec les clés Supabase actuelles et historiques.

## Ce que vous devez remplacer
- Sources Python/HTML du projet, puis reconstruire l'application Windows.
- Code de l'Edge Function Supabase `username-login`.

## Étape A — Déployer la fonction corrigée
1. Ouvrir Supabase → Edge Functions → `username-login`.
2. Remplacer tout le code par `supabase/functions/username-login/index.ts` de cette version.
3. Déployer la fonction.
4. Dans les détails de la fonction, désactiver **Verify JWT** pour `username-login` uniquement.
5. Tester l'URL de la fonction en GET. Réponse attendue : `{"ok":true,"service":"username-login","version":"1.7.9.1"}`.

La fonction vérifie elle-même le mot de passe avec Supabase Auth. Le endpoint est donc pré-authentification. Ne désactivez pas Verify JWT pour `admin-users` ou `auth-event`.

## Étape B — Vérifier la migration 0007
La fonction utilise `consume_username_login_attempt` et `reset_username_login_attempts`. Si la migration `0007_username_login_security.sql` a déjà été exécutée et que `username_login_attempts` existe, ne la relancez pas. Sinon, exécutez une fois le fichier `supabase/migrations/0007_username_login_security.sql` dans SQL Editor.

## Étape C — Mettre à jour l'application
1. Fermer W-A Systeme de Gestion.
2. Extraire le ZIP dans un nouveau dossier.
3. Copier les fichiers du dossier `wa-management` vers le dépôt local existant en conservant `.git`.
4. Ne pas copier les anciens dossiers `build` ou `dist` par-dessus le projet.
5. Lancer `build_exe.bat` une fois.
6. Ouvrir le nouvel exécutable dans le dossier `dist` (ou le dossier de sortie alternatif imprimé par le build).

La configuration locale `cloud_config.json` n'est pas modifiée. Ne relancez pas `configure_cloud.bat` sauf si l'URL ou la clé Publishable a réellement changé.

## Étape D — Tests
1. Se connecter avec l'e-mail d'un utilisateur existant et son mot de passe actuel.
2. Se déconnecter, puis se connecter avec son nom d'utilisateur et le même mot de passe.
3. Tester `destrox` avec le mot de passe existant du Superadmin.
4. Créer un compte test avec un mot de passe employé de 6 à 8 caractères, dont un code numérique si la politique Supabase l'autorise.
5. Supprimer le compte test après validation.

## Diagnostic des erreurs
- HTTP 404 / fonction introuvable : la fonction `username-login` n'est pas déployée sous ce nom.
- `Invalid JWT`, `Invalid Token` ou `Missing authorization header` : désactiver Verify JWT pour `username-login` et redéployer.
- HTTP 503 / configuration incomplète : vérifier la migration 0007 et les variables d'environnement intégrées de Supabase Edge Functions. La fonction doit disposer de `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEYS` et `SUPABASE_SECRET_KEYS` (ou anciennes variables prises en charge).
- Identifiant ou mot de passe incorrect : le service est accessible, mais l'identifiant ou le mot de passe ne correspond pas à Supabase Auth.

## Sécurité
- Le desktop contient uniquement l'URL et la clé Publishable/anon.
- La clé Secret/service-role reste dans les variables d'environnement de Supabase Edge Functions.
- Les réponses d'échec ne renvoient jamais l'e-mail trouvé pour un nom d'utilisateur.
- Les mots de passe existants plus longs continuent de fonctionner. La limite de 6 à 8 caractères concerne les nouveaux mots de passe des comptes employés, pas la connexion aux mots de passe existants.
