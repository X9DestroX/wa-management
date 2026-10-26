# W-A Systeme de Gestion v1.6.2

- Nouvelle icône officielle EA fournie par l’entreprise pour l’application Windows.
- Nom de l’application remplacé partout par « W-A Systeme de Gestion ».
- Le nom du dossier/exécutable généré par PyInstaller est désormais « W-A Systeme de Gestion ».
- Les chemins internes de données `%USERPROFILE%\WA_Manager_System` sont conservés pour ne pas perdre les bases existantes lors de la mise à niveau.

# W-A Systeme de Gestion v1.6.1

- GPS: SIM + activation fixed at 3,000 FCFA and includes month 1.
- Nombre d’abonnement now means additional months and can be 0.
- Total abonnement = additional months × 3,000 FCFA.
- Total à payer = Montant + 3,000 FCFA + Total abonnement.
- Added stored total_amount for dashboard and sales records.
- Existing LAN, French interface, editing/deletion and authorization features retained.

# v1.6.0

## GPS
- Formulaire GPS simplifié selon les nouveaux champs demandés.
- Montant final vide et saisi manuellement.
- SIM + Activation fixe à 3 000 FCFA, incluant le premier mois.
- Abonnement fixe à 3 000 FCFA/mois.
- Total abonnement calculé automatiquement selon le nombre de mois.
- Type GPS : Moto, Voiture, Camion.
- Suppression de l'interface pour prix d'installation, abonnement réel/mois, avantage/remise, activation du mois suivant et dépense/jour.

## Ventes
- Modification et suppression conservées.
- Historique adapté aux nouveaux champs.
- Anciennes données SQLite conservées pour compatibilité/migration.

## Réseau
- Ajout d'une liste blanche IP serveur pour limiter l'accès aux PC clients autorisés.
- Jusqu'à 2 PC clients autorisés, soit 3 laptops au total avec le serveur.
- Ajout de configure_lan_access.bat.
- Pare-feu LAN documenté et script mis à jour.
- Détection de l'IP locale sans dépendre d'Internet.

## v1.6.4
- Starlink sale form keeps only the amount payable plus Date et heure and Note.
- Date/time and notes are visible for both GPS and Starlink in new-sale and edit-sale forms.
- GPS-specific fields remain hidden for Starlink.
