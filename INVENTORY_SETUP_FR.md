# Mise en place du catalogue produit et stock — v1.7.6

## Avant le build
1. Dans Supabase SQL Editor, exécuter `supabase/migrations/0006_product_inventory.sql` une seule fois.
2. Vérifier `public.products`, `public.stock_movements`, `sales.product_id` et `sales.quantity`.
3. Copier les fichiers source dans le dépôt local; conserver `.git`.
4. Exécuter `build_exe.bat` sur le PC de développement puis tester avec un produit de test.

## Champs du produit
- Catégorie
- Nom du produit
- Code-barres / QR code
- Prix de vente (FCFA)
- Quantité en stock
- Notes

## Comportement du stock
- À la création du produit, la quantité initiale est enregistrée dans `stock_movements`.
- Une vente du catalogue crée une sortie de stock négative. La validation finale et l’écriture du stock se font dans des triggers PostgreSQL transactionnels afin d’éviter la vente simultanée d’un stock insuffisant.
- Modifier produit/quantité sur une vente restitue l’ancienne quantité puis déduit la nouvelle.
- Supprimer une vente restitue la quantité dans le stock.
- Modifier manuellement la quantité dans le formulaire produit ajoute un mouvement d’ajustement.
- Archiver un produit le rend indisponible aux nouvelles ventes sans supprimer ses historiques.

## Vérification rapide
1. Créer un produit test avec 5 unités.
2. Vérifier un mouvement `stock_initial` avec +5.
3. Vendre 1 : stock = 4. Modifier la vente à 2 : stock = 3.
4. Supprimer la vente : stock = 5.
5. Vérifier que les mouvements apparaissent dans « Historique des mouvements de stock ».

## Scanner et importation (v1.7.7)
- Le formulaire produit comprend un bouton **Scanner** utilisant la caméra lorsqu’elle est disponible. Le champ manuel reste compatible avec les lecteurs USB qui saisissent comme un clavier.
- L’import accepte `.xlsx` et `.csv`, affiche un aperçu avant import, signale les lignes invalides et détecte les doublons de code-barres/QR.
- Le modèle `products_import_template.csv` utilise les six colonnes du catalogue et peut être ouvert dans Excel.
- Limites : fichiers jusqu’à 8 Mo, 1 000 lignes de produits par fichier. Les fichiers Excel `.xls` doivent être enregistrés en `.xlsx`.
- La lecture par caméra dépend des permissions du navigateur et de son support caméra. Pour l’accès par téléphone via URL partagée, il faudra encore déployer la version web sur HTTPS.
