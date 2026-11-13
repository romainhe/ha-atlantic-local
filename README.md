# Atlantic local

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/romainhe/ha-atlantic-local)](LICENSE)

Intégration Home Assistant qui pilote un radiateur ou sèche-serviettes Atlantic connecté **en local**, en parlant directement au serveur web de son module Wi-Fi (`wifi-gw`). Aucun compte Cozytouch, aucun cloud.

Testée sur un sèche-serviettes **Doris 2000 W** (`TRI TD1W`, firmware module `v1.5.2`).

## État / Statut

Version actuelle : **v0.2**.

- ✅ **Fonctionne** — consigne (ID 4118), marche/arrêt (4015), boost avec type (serviette seule ou + ventilation) et durée réglables, heure de fin du boost, compteur d'énergie interne (tableau Énergie sans cloud) et puissance de chauffe. Tous les IDs ont été validés par écriture sur le radiateur. Config par IP, traduit FR/EN, CI verte. Contrôle sans cloud, contourne le bug Cozytouch #186.
- ⬜ **Non géré** — programmation hebdomadaire (IDs 4126–4132 lus mais non exposés).
- ⬜ **À faire** — fixer l'IP du module par un bail DHCP statique sur la box ; installation via HACS et test de bout en bout dans Home Assistant.

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
| `climate` — consigne, température ambiante, bornes min/max | IDs 4118, 4104, 4110, 4111 |
| `climate` — modes Chauffe / Arrêt | ID 4015 (4 = marche, 0 = arrêt) |
| `climate` — preset Boost / Aucun | ID 4044 (1 = lancer, 0 = arrêter) |
| `select` Type de boost — Serviette / Serviette + ventilation (configuration) | ID 4045 |
| `number` Durée du boost, 5 à 60 min par pas de 5 (configuration) | ID 4046 |
| `climate` — action Chauffe / Inactif / Arrêt | ID 8503 > 0 = chauffe |
| `sensor` Fin du boost (horodatage, inconnu hors boost) | ID 4048 |
| `sensor` Énergie — compteur interne du radiateur, kWh, `total_increasing` (tableau Énergie) | ID 4041 (Wh) |
| `sensor` Puissance de chauffe — % de la puissance demandée par la régulation | ID 8503 |
| `sensor` Température ambiante | ID 4104 |
| `sensor` Température interne (diagnostic) | ID 4103 |
| `sensor` Signal Wi-Fi (diagnostic, désactivé par défaut) | ID 822 |

La durée du boost n'est lue par le radiateur qu'au lancement : la modifier pendant un boost ne change pas son heure de fin. Pour l'appliquer tout de suite, repasser le preset sur Aucun puis Boost. Le type, lui, s'applique à chaud. Éteindre le radiateur coupe le boost en cours.

Cartographie complète et pièges : [`docs/mapping-modes.md`](docs/mapping-modes.md).

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
| 4015 | Marche / arrêt (4 / 0) — 4030 et 4083 en sont des miroirs, à ne pas écrire |
| 4019 | Nom de la pièce |
| 4041 | Énergie consommée, Wh cumulés (même compteur que la conso cloud Atlantic) |
| 4044 | Boost (1 / 0) |
| 4045 | Type de boost (0 serviette, 1 + ventilation) |
| 4046 | Durée du boost (min) |
| 4048 | Fin du boost (heure locale encodée en epoch UTC) |
| 4081, 4082 | Suivent la consigne |
| 4103 | Température interne |
| 4104, 4109 | Température ambiante |
| 4110 / 4111 | Consigne min / max |
| 4118 | Consigne |
| 4120, 4135, 4141 | Consigne confort du programme (probable) |
| 8503 | Puissance de chauffe demandée (%) |
| 4126 – 4132 | Programme hebdomadaire : paires minute de début / consigne |

## Développement

```bash
./scripts/setup     # venv, HA, ruff, tests, symlink custom_components → config/
./scripts/develop   # hass --config ./config --debug
pytest -q
```
