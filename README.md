## Version 1.6.3 — Mise à jour Starlink

**Attention : la synchronisation cloud n'est pas encore activée.** Cette version utilise encore le serveur LAN/SQLite existant. Consultez `SUPABASE_MIGRATION_NEXT_STEPS.md` avant de prévoir un usage entre sites distants.

# W-A Systeme de Gestion v1.6.0 — GPS simplifié + LAN sécurisé

Version Windows avec interface entièrement en français, autorisations utilisateurs et fonctionnement LAN/WLAN pour 1 serveur + jusqu'à 2 PC clients.

## 1. Nouvelle saisie GPS

Pour une vente GPS, les champs sont maintenant :

- Nom du client
- Numéro de téléphone
- Montant — **saisi manuellement**, vide par défaut
- Numéro du SIM
- Type du GPS : **Moto / Voiture / Camion**
- Adresse
- SIM + Activation : **3 000 FCFA** (inclut le premier mois)
- Abonnement : **3 000 FCFA / mois**
- Date et heure
- Nombre d'abonnement
- Total d'abonnement — calculé automatiquement : 3 000 × nombre de mois
- Abonnement effectué : Oui / Non
- Note

### Champs retirés de la saisie GPS

- Prix d'installation
- Abonnement réel / mois
- Avantage / remise
- Activation du mois suivant
- Dépense / jour
- Installé par
- Ancien numéro de téléphone de l'appareil

Les anciennes colonnes SQLite restent uniquement pour permettre la migration des anciennes données; elles ne sont plus affichées ni saisies.

## 2. Modification et suppression

Les boutons **Modifier** et **Supprimer** restent disponibles dans le registre des ventes et dans Finance / Dépôts.

- RH : opérations courantes et modification/suppression des ventes et dépôts.
- Gestionnaire : opérations courantes et modification/suppression des ventes et dépôts.
- Administrateur : toutes les opérations + gestion des utilisateurs.

Seul l'**Administrateur** peut créer, modifier ou supprimer un utilisateur.

## 3. Réseau : 1 serveur + 1 ou 2 clients

Le modèle recommandé est :

```text
                    Réseau privé LAN/WLAN
                           │
                 ┌─────────┴─────────┐
                 │                   │
          PC 1 — SERVEUR       PC 2 — CLIENT
          Base de données      W-A Systeme de Gestion
                 │
                 └────────────── PC 3 — CLIENT (optionnel)
```

La base SQLite reste uniquement sur le serveur. Les clients utilisent le serveur via HTTP; ils ne partagent jamais directement le fichier `.db`.

### Limitation d'accès

v1.6.0 ajoute une liste blanche IP côté serveur. Elle permet d'autoriser seulement **1 ou 2 PC clients**.

Le fichier serveur est :

`%USERPROFILE%\WA_Manager_System\lan_access.json`

Exemple pour deux clients :

```json
{
  "enabled": true,
  "max_clients": 2,
  "allowed_ips": ["192.168.50.2", "192.168.50.3"]
}
```

Une machine dont l'IP n'est pas dans cette liste reçoit un refus d'accès, même si elle connaît l'adresse du serveur.

## 4. Configuration recommandée — Wi-Fi / routeur

C'est la méthode la plus simple.

1. Connecter le serveur et les 1–2 clients au **même Wi-Fi ou même switch/routeur**.
2. Mettre le réseau Windows en **Privé**.
3. Donner des adresses IP fixes ou des réservations DHCP aux PC. Exemple :
   - Serveur : `192.168.50.1`
   - Client 1 : `192.168.50.2`
   - Client 2 : `192.168.50.3`
4. Sur le serveur, lancer `setup_firewall.bat` avec **Exécuter en tant qu'administrateur**.
5. Sur le serveur, lancer `configure_lan_access.bat` et saisir les IP des PC clients.
6. Lancer W-A Systeme de Gestion sur le serveur.
7. Lancer W-A Systeme de Gestion sur les clients.
8. Le serveur doit afficher **Serveur LAN** et les autres **LAN connecté**.

Internet n'est pas nécessaire pour le fonctionnement de l'application sur le réseau local.

## 5. Connexion directe Ethernet entre PC

Pour deux PC reliés directement par câble Ethernet, utiliser par exemple :

- Serveur : IP `192.168.50.1`, masque `255.255.255.0`
- Client : IP `192.168.50.2`, masque `255.255.255.0`

Pour trois PC, utiliser `192.168.50.3` pour le deuxième client.

Aucun Internet n'est nécessaire.

## 6. Ports

- Application : TCP **8765**
- Découverte LAN : UDP **8766**

Le pare-feu doit autoriser ces ports sur le profil **Privé**.

## 7. Fichiers utiles

- `setup_firewall.bat` — ouvre les ports LAN nécessaires.
- `configure_lan_access.bat` — configure les PC clients autorisés.
- `reset_network_config.bat` — réinitialise la configuration automatique LAN.
- `lan_access_example.json` — exemple de liste blanche.

## 8. Sauvegardes

Les sauvegardes automatiques de la base serveur sont conservées dans :

`%USERPROFILE%\WA_Manager_System\backups`

Les 14 sauvegardes les plus récentes sont conservées.

## 9. Nom et icône de l’application

Le logiciel est distribué sous le nom **W-A Systeme de Gestion** avec l’icône officielle fournie.

> Compatibilité : le dossier interne `%USERPROFILE%\WA_Manager_System` est conservé volontairement afin que les installations précédentes retrouvent leurs données existantes.

### Starlink form (v1.6.4)
For Starlink sales, the form displays only **Montant à payer**, **Date et heure**, and **Note** (in addition to the device type selector). GPS-specific fields remain hidden. These same fields are available when editing a Starlink sale.
