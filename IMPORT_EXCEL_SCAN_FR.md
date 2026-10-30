# W-A Systeme de Gestion v1.7.7 — Scanner et importation Excel/CSV

## Nouveautés
- Scan par caméra dans le formulaire produit (webcam sur PC; caméra disponible dans les navigateurs compatibles). Le scan utilise l'API BarcodeDetector si elle est prise en charge, avec une solution de secours `html5-qrcode` chargée depuis Internet.
- Bouton pour saisir un code avec lecteur USB/scanner clavier ou manuellement toujours disponible.
- Import des fichiers `.xlsx` et `.csv` avec aperçu avant enregistrement.
- Les doublons de code-barres/QR existants ou répétés dans le fichier sont signalés et ignorés; les lignes mal formées ne sont pas importées.
- Les produits importés créent leurs mouvements de stock initial via le trigger Supabase (en mode cloud) ou via le serveur SQLite local.
- Taille maximale : 8 Mo. Maximum : 1 000 produits par fichier. Les anciens fichiers `.xls` doivent être enregistrés au format `.xlsx`.

## Format Excel / CSV
La première ligne doit contenir des en-têtes. Le modèle est `products_import_template.csv`, ouvrable dans Excel. Colonnes :
- `Catégorie` (obligatoire)
- `Nom du produit` (obligatoire)
- `Code-barres / QR code` (facultatif mais recommandé; doit être unique s'il est renseigné)
- `Prix de vente` (obligatoire, FCFA)
- `Quantité en stock` (obligatoire, entier >= 0)
- `Notes` (facultatif)

Le fichier CSV accepte la virgule, le point-virgule ou la tabulation comme séparateur. Enregistrez les feuilles Excel au format `.xlsx`.

## Test recommandé
1. Créer un produit test avec un code unique.
2. Télécharger le modèle CSV, remplir deux produits puis importer.
3. Vérifier l'aperçu, puis confirmer l'import.
4. Importer une deuxième fois le même fichier : les codes en doublon doivent être signalés et non réimportés.
5. Scanner un code QR ou code-barres avec la caméra autorisée et vérifier que le champ est rempli.

## Sécurité / fonctionnement
L'import passe par l'API de l'application et utilise la session de l'employé connecté. Il ne nécessite ni clé service-role ni nouvel SQL de Supabase. La protection d'unicité du code-barres dans Supabase reste une dernière barrière contre les doublons concurrents. La caméra nécessite l'autorisation du navigateur et une connexion Internet pour charger la solution de secours de lecture si l'API native n'existe pas.
