# Configuration du Superadmin système `destrox`

Ce guide configure le nom d'utilisateur exact **`destrox`**. Le mot de passe et l'adresse e-mail sont choisis par le propriétaire et ne doivent pas être partagés dans le dépôt GitHub ou le chat.

## Ordre à suivre

1. Dans Supabase → **SQL Editor**, exécutez le fichier `supabase/migrations/0005_superadmin_protection.sql` de ce package corrigé. Il ajoute le rôle `Superadmin` et installe/remplace le déclencheur qui protège le compte `destrox`. Le fichier peut être réexécuté : il remplace le déclencheur et la fonction.
2. Dans Supabase → **Authentication → Users**, créez l'utilisateur avec l'adresse e-mail que vous avez choisie et un mot de passe fort.
3. Copiez `supabase/migrations/PROMOTE_DESTROX_TEMPLATE.sql` dans une nouvelle requête SQL, remplacez `REPLACE_WITH_SUPERADMIN_EMAIL` par l'adresse exacte (en gardant les apostrophes), puis exécutez. Le résultat doit afficher `username = destrox` et `role = Superadmin`.
4. Dans Supabase → **Edge Functions → admin-users**, remplacez le code par `supabase/functions/admin-users/index.ts` de ce package et redéployez.
5. Copiez le code source corrigé dans votre dépôt local (gardez `.git`) et exécutez `build_exe.bat`. Distribuez le dossier complet `dist/W-A Systeme de Gestion` après un test réussi.

## Si vous aviez déjà utilisé la mauvaise orthographe

Exécutez d'abord l'étape 1 ci-dessus pour remplacer le déclencheur qui protégeait l'ancienne orthographe. Ensuite exécutez l'étape 3 pour renommer le profil existant `Superadmin` en `destrox`, sans créer un deuxième compte Auth. Si l'étape 3 échoue, arrêtez et vérifiez `public.profiles` et `auth.users` avant de créer un autre utilisateur.

## Vérification

La dernière requête du fichier de promotion doit retourner exactement le profil Superadmin attendu, avec le nom `destrox`, la bonne adresse e-mail et le rôle `Superadmin`. Un Administrateur ordinaire ne doit pas pouvoir modifier ou supprimer ce compte; `destrox` peut gérer les autres comptes. Le compte Superadmin ne peut pas supprimer son propre compte depuis l'application.

Ne placez jamais une clé Supabase Secret/service-role ou le mot de passe de `destrox` dans le client Windows ou GitHub.
