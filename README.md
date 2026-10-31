# W-A Systeme de Gestion v1.7.9.1 — Correctif de connexion

Cette version corrige l'expérience de connexion de la v1.7.9.

## Correctifs
- Retrait du texte « Exemple : admin, yassir, hr ou votre adresse e-mail professionnelle » sous le champ d'identifiant.
- Connexion par nom d'utilisateur ou par adresse e-mail conservée.
- Résolution du nom d'utilisateur effectuée uniquement dans l'Edge Function Supabase `username-login`.
- La fonction utilise des requêtes HTTP Supabase avec les nouvelles clés `sb_publishable_*` / `sb_secret_*` dans l'en-tête `apikey`, sans envoyer une clé API opaque comme jeton Bearer. Les anciennes clés JWT restent compatibles.
- Messages de diagnostic plus précis pour la fonction absente, Verify JWT activé, migration 0007 ou configuration Edge Function incomplète.
- Aucun changement aux tables ou données métier : ventes, dépôts, dépenses, produits, stock, rapports et journaux sont conservés.

## Mise à jour obligatoire
Suivre `LOGIN_FIX_SETUP_FR.md`. Déployer d'abord le nouveau code de `username-login` dans Supabase, désactiver Verify JWT pour cette fonction uniquement, vérifier la migration 0007, puis reconstruire le desktop avec `build_exe.bat`.

Ne relancez pas les migrations déjà appliquées. Ne mettez jamais la clé Supabase Secret/service-role dans le desktop ou GitHub.
