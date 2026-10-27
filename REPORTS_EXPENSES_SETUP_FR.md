# v1.7.3 — Rapports et dépenses : installation

## Ce qui est ajouté
- Menu **Rapports** avec choix hebdomadaire (lundi à dimanche) et mensuel (mois civil).
- Export direct d’un PDF multipage : ventes GPS, ventes Starlink, abonnements, dépôts, dépenses d’entreprise, anciennes dépenses associées aux ventes et synthèse des montants.
- Registre séparé des dépenses d’entreprise dans **Finance / Dépôts**, avec ajout, modification et suppression.
- Prise en compte des nouvelles dépenses dans le tableau de bord.

## À faire AVANT de compiler et d'utiliser la nouvelle version cloud
1. Dans le tableau de bord Supabase `wa-management`, ouvrez **SQL Editor → New query**.
2. Copiez le fichier `supabase/migrations/0002_company_expenses.sql` et exécutez-le. Il crée `public.expenses` avec RLS. Il ne supprime aucune donnée existante.
3. Vérifiez dans **Table Editor** que la table `expenses` existe.
4. Copiez les fichiers source de ce dossier dans votre dépôt GitHub local, sans écraser le dossier `.git`. Gardez `.gitignore` et ne publiez pas `cloud_config.json`, bases SQLite ou secrets.
5. Exécutez `build_exe.bat`. Le build installe ReportLab et le regroupe dans l'exécutable.
6. Lancez `dist/W-A Systeme de Gestion/W-A Systeme de Gestion.exe`. La configuration Supabase existante est conservée dans `%USERPROFILE%\WA_Manager_System\cloud_config.json`; il n'est pas nécessaire de configurer le cloud une deuxième fois.

## Interprétation des rapports
- **Chiffre d’affaires** : somme des ventes enregistrées (pour GPS, total payé comprenant montant de base, SIM + activation et mois supplémentaires; pour Starlink, montant à payer).
- **Abonnements** : somme des abonnements supplémentaires stockés sur les ventes. Les 3 000 FCFA SIM + activation couvrant le premier mois sont déjà dans le total GPS, ils ne sont pas comptés une seconde fois dans cette ligne.
- **Dépôts financiers** : somme des dépôts de compte; montrée séparément, non additionnée au chiffre d’affaires.
- **Dépenses entreprise** : nouvelles lignes du registre des dépenses.
- **Dépenses liées aux ventes** : champ historique `sales.expenses`, affiché séparément afin de ne pas le confondre avec les nouvelles charges.
- **Position opérationnelle** : chiffre d’affaires moins toutes les dépenses enregistrées; les dépôts ne sont pas traités comme un revenu.

Les PDF sont générés localement à partir des données déjà autorisées pour la session. Le service-role key n'est ni nécessaire ni inclus. Les rapports se fondent sur les données saisies; ils ne peuvent pas calculer des dépenses qui n'ont pas été enregistrées.


## v1.7.3.2 — Où retrouver le PDF

Quand vous cliquez sur **Exporter le rapport en PDF**, le programme enregistre le PDF directement dans le dossier **Téléchargements** de Windows (ou le dossier Téléchargements redirigé dans Windows). Une boîte de dialogue indique le nom du fichier et son chemin complet. Vous pouvez copier le chemin affiché dans la barre d’adresse de l’Explorateur de fichiers Windows. Chaque export inclut l’heure dans le nom du fichier afin de ne pas écraser un rapport précédent.
