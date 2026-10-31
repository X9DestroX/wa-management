# CHANGELOG

## 1.7.9.1 — Correctif de connexion
- Suppression du texte d’exemple sous le champ de connexion.
- Connexion par nom d’utilisateur conservée via l’Edge Function `username-login`; connexion par e-mail conservée.
- Edge Function réécrite pour utiliser les clés Supabase actuelles et historiques avec les en-têtes API appropriés.
- Messages de diagnostic plus précis pour les erreurs de déploiement et de configuration.

## 1.7.9.1 — Correctif de connexion
- Suppression du texte d'exemple sous le champ de connexion.
- Connexion par nom d'utilisateur conservée via l'Edge Function `username-login`.
- Réécriture de `username-login` en appels HTTP directs avec en-tête `apikey`, compatible avec les nouvelles clés Supabase `sb_publishable_*` et `sb_secret_*` et les anciennes clés JWT.
- Messages d'erreur plus précis pour distinguer fonction non déployée, Verify JWT actif, migration 0007 absente, configuration Edge Function et identifiants incorrects.
- Ajout d'une vérification de déploiement GET sans exposer d'identifiants ni de secrets.
- Connexion par e-mail conservée.
- Aucun changement aux données métier, produits, stocks, ventes, dépôts, dépenses, rapports PDF ou journaux.

## 1.7.9 — Connexion par nom d'utilisateur
- Connexion via nom d'utilisateur ou e-mail.
- Nouveaux mots de passe employés de 6 à 8 caractères via la gestion des comptes.
