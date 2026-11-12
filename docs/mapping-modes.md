# Cartographie des modes — protocole

Lecture seule. Lancer `python3 scripts/map_ids.py 192.168.1.22`, puis pour chaque ligne : faire le changement sur le radiateur, attendre 2-3 s, taper le libellé.

Partir du mode programme, consigne 20 °C.

| # | Action sur le radiateur | Libellé à taper | Attendu |
|---|---|---|---|
| 1 | Mode confort (manuel) | `confort` | id de mode + consigne active |
| 2 | Mode éco | `eco` | même id de mode, autre valeur ; consigne → éco |
| 3 | Hors-gel | `hors-gel` | id de mode ; consigne 7 °C ? |
| 4 | Boost | `boost` | id boost / durée (4138 = 120 ?) |
| 5 | Arrêt | `arret` | marche/arrêt |
| 6 | Marche | `marche` | retour |
| 7 | Retour programme | `programme` | id de mode = valeur initiale |
| 8 | Consigne éco −1 °C (si réglable) | `eco-1` | id consigne éco |
| 9 | Consigne confort +1 °C | `confort+1` | 4120/4135/4141 ? |

Candidats repérés dans le bloc 4000 (valeurs le 2026-11-12, mode programme, 20 °C) :
4020=40, 4021=2, 4023=1, 4026=2, 4027=9, 4030=4, 4105=18, 4106=10, 4107=20,
4108=35, 4123=1, 4124=42, 4125=6, 4133=15, 4134=60, 4138=120, 4142=50.

Ensuite : vérifier par une écriture test (avec accord) que l'id de mode s'écrit avec sa clé typée, puis exposer `preset_modes` et `HVACMode.OFF` dans `climate.py`.
