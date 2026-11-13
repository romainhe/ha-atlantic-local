# Cartographie des modes — Doris 2000 W

Établie le 2026-11-13 : relevés en lecture (`scripts/map_ids.py`) pendant des changements faits à la main, puis chaque ID validé par une écriture (`CMD 3`, `SN 13`, clé `VIU`) relue derrière.

Le Doris n'expose que marche/arrêt, consigne et boost : pas de confort / éco / hors-gel côté module. La programmation hebdomadaire (4126–4132) n'est pas gérée.

## IDs validés

| ID | Rôle | Valeurs | Écriture |
|---|---|---|---|
| 4015 | Marche / arrêt | 4 = marche, 0 = arrêt | ✅ commande l'arrêt et la remise en marche |
| 4030, 4083 | Miroirs de 4015 | 4 / 0 | ⚠️ écrire 4030 = 0 n'éteint pas : ça annule seulement le boost en cours |
| 4118 | Consigne (`VIS`) | centièmes de °C | ✅ |
| 4044 | Boost | 1 = lancer, 0 = arrêter | ✅ effet immédiat |
| 4045 | Type de boost | 0 = serviette seule, 1 = serviette + ventilation | ✅ pris en compte à chaud |
| 4046 | Durée du boost | minutes, paliers de 5 | ✅ lue **au lancement** seulement : la changer pendant un boost ne décale pas la fin ; relancer (4044 = 0 puis 1) pour l'appliquer |
| 4048 | Fin du boost | horodatage, 0 hors boost | lecture seule : calculé par le radiateur (l'écrire ne lance rien) |

4048 contient l'heure **locale** encodée comme un epoch UTC : 1794571834 = 2026-11-13 12:10:34 heure de Paris. Éteindre le radiateur coupe le boost en cours.

## Autres IDs observés

| ID | Comportement |
|---|---|
| 4039, 4090 | Passent à 1 avec le boost ; 4090 passe aussi à 1 sur toute action manuelle (dérogation), y compris à l'arrêt |
| 8504 / 8524 | Sorties serviette / ventilation (1 = active) |
| 4041 | Énergie cumulée en Wh : +139 Wh en 4 min de boost à 2 kW, plat à l'arrêt ; égale à la conso cloud Atlantic (496,344 kWh à 11:06 entre 496273 et 496412 lus à 11:03 et 11:07) |
| 8503, 4091 | Puissance demandée (%, ×100 pour 4091) : sortie de régulation, pas un état de boost. 8503 alimente `hvac_action` et le sensor Puissance de chauffe |
| 4047 | 30, inchangé dans tous les relevés : rôle inconnu |

## Refaire une cartographie

Lecture seule. Lancer `python3 scripts/map_ids.py 192.168.1.22`, puis pour chaque changement fait sur le radiateur : attendre 2-3 s et taper un libellé. Les IDs qui ont changé s'affichent et tout est journalisé dans `mapping-<horodatage>.jsonl`. Le module ne traite qu'une requête à la fois (~0,4 s) : un balayage complet des blocs prend plus de 2 min.
