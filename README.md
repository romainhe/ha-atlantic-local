# Atlantic local

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/romainhe/ha-atlantic-local)](LICENSE)

Intégration Home Assistant qui pilote un radiateur ou sèche-serviettes Atlantic connecté **en local**, en parlant directement au serveur web de son module Wi-Fi (`wifi-gw`). Aucun compte Cozytouch, aucun cloud.

Testée sur un sèche-serviettes **Doris 2000 W** (`TRI TD1W`, firmware module `v1.5.2`).

## Installation

### HACS (dépôt custom)

1. HACS → Intégrations → ⋮ → Dépôts personnalisés.
2. Ajouter `https://github.com/romainhe/ha-atlantic-local`, catégorie **Integration**.
3. Installer, puis redémarrer Home Assistant.

### Manuelle

Copier `custom_components/atlantic_local/` dans `config/custom_components/` puis redémarrer Home Assistant.

## Configuration

**Paramètres → Appareils et services → Ajouter une intégration → Atlantic local**, puis saisir l'adresse IP du module Wi-Fi. Fixer cette IP avec un bail DHCP statique sur la box. Si elle change, **Reconfigurer** l'entrée.

L'intervalle d'interrogation (30 s par défaut) se règle dans **Configurer**.

## Entités

| Entité | Source |
|---|---|
| `climate` — consigne (lecture / écriture), température ambiante, bornes min/max | IDs 4118, 4104, 4110, 4111 |
| `sensor` Température ambiante | ID 4104 |
| `sensor` Température interne (diagnostic) | ID 4103 |
| `sensor` Signal Wi-Fi (diagnostic, désactivé par défaut) | ID 822 |

Les modes (arrêt, confort, éco, boost, hors-gel, programme) ne sont pas encore exposés : seul le mode chauffage avec consigne est disponible.

## Protocole

Le module expose `POST /passthrough/cmd`, sans authentification. Une commande par requête : le module ignore les suivantes d'un même tableau.

Lecture :

```json
[{"CMD": 1, "SN": 4118, "ID": 4118}]
```

Réponse (le champ `payload` est une chaîne JSON) :

```json
{"message": "Post Action Received", "payload": "[{\"CMD\":2,\"SN\":4118,\"ID\":4118,\"VIS\":2000,\"STATUS\":2}]", "success": true}
```

- `STATUS 2` : valeur présente, sous une clé typée — `VIU` entier, `VIS` entier signé, `VS` texte, `VTIU`/`VTIS` listes, `VC`/`VTC` structures.
- `STATUS 10` + `ERROR 6` ou `7` : ID inconnu du module.

Écriture :

```json
[{"CMD": 3, "SN": 13, "ID": 4118, "VIS": 1950}]
```

La valeur doit être envoyée sous **la même clé typée qu'en lecture**. La page de maintenance du module (`/dm/dm_act.html`) envoie une clé `value` générique, que le module refuse avec `ERROR 4` : c'est pour ça que cette page ne fonctionne pas.

Les températures sont en centièmes de degré. Les IDs locaux n'ont rien à voir avec les capabilities de l'API cloud Cozytouch / Magellan.

### IDs connus (Doris 2000 W)

| ID | Valeur |
|---|---|
| 1 | Numéro de série |
| 50 / 51 | Code produit / modèle |
| 503 | Firmware du module |
| 822 | RSSI Wi-Fi (dBm) |
| 4019 | Nom de la pièce |
| 4081, 4082 | Suivent la consigne |
| 4103 | Température interne |
| 4104, 4109 | Température ambiante |
| 4110 / 4111 | Consigne min / max |
| 4118 | Consigne |
| 4120, 4135, 4141 | Consigne confort du programme (probable) |
| 4126 – 4132 | Programme hebdomadaire : paires minute de début / consigne |

## Développement

```bash
./scripts/setup     # venv, HA, ruff, tests, symlink custom_components → config/
./scripts/develop   # hass --config ./config --debug
pytest -q
```
