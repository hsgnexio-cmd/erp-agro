# Prochaine étape : partie 7b – Préparation et expédition

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md`.

## 1. Où en est le projet (fin de la partie 7a)

- Phases 1 à 6 terminées et fusionnées ; partie 7a (tarifs de vente, commandes clients, EDI simulé) fusionnée (pull request n° 7).
- Branche de travail **`phase-7b-expedition`** déjà créée à partir de `main` ; elle contient uniquement la mise à jour de la documentation (ce fichier, `CLAUDE.md`, `docs/decisions.md`).
- Tests : 294 back-end (pytest) et 30 front-end (Vitest), tous verts.
- Existant utile pour la 7b :
  - `ventes/services.py` : `record_shipment` (expédition minimale de la phase 5 : lot libéré, non périmé, MDD chez son enseigne, DLC minimale **à la date du jour**, mouvement `expedition` relié à l'entrepôt client) et `check_lot_for_customer`.
  - `ventes/orders.py` : commandes clients (statuts `recue` → `en_preparation` → `expediee`, ou `annulee`), heure limite 11 h, produits commandables.
  - `stocks/services.py` : `fefo_plan(article, site, quantity, min_expiry_date=…)` (paramètre prévu pour la règle 5), `quantity_at`, `block_lot`.
  - `stocks/monitoring.py` : `raise_alert` (alertes), `temperature_limits`.
  - `production/orders.py` : modèle à suivre pour une proposition FEFO pré-remplie avec justification hors FEFO (`proposal`, `declare_production`).
  - Stock de produits finis de démonstration à la plateforme : lots de lasagnes et de gratin en `PFN-FRAIS-A` (phase 5) ; les OF de la phase 6 ne sont pas encore déclarés (beaucoup de commandes seront donc en rupture si on ne fabrique pas d'abord).

## 2. Décisions déjà validées par Nicolas (plan de la phase 7)

| N° | Décision |
| --- | --- |
| 5 | Le **magasinier** (et l'admin) prépare et expédie ; tous les rôles consultent. |
| 6 | **DLC minimale client à la date de livraison demandée** : DLC du lot ≥ date de livraison + durée de vie × % exigé par l'enseigne (ex. lasagnes 14 j, ENS1 70 % → au moins 9,8 jours restants). Les lots trop courts ne sont pas proposés pour cette enseigne. |
| 7 | **Pas de reliquat** (produits frais) : la quantité non servie est une **rupture**, la ligne est soldée. |
| 8 | **Température obligatoire à l'expédition** ; au-dessus de 4 °C : expédition **refusée**, lots préparés **bloqués**, **alerte** critique (règle 7). |
| 9 | **Palettes** : 60 colis de 12 = **720 unités** maximum, découpage automatique ; **SSCC** à 18 chiffres, norme GS1, préfixe d'entreprise fictif, clé de contrôle calculée. |
| 10 | **Taux de service** = quantité livrée complète et à l'heure ÷ quantité commandée, par enseigne et par période ; « à l'heure » = expédié au plus tard la veille de la date de livraison (transport J+1) ; objectif **98,5 %**, pénalités non calculées (seulement signalées). Tableaux de bord complets en phase 8. |

## 3. Points à faire valider au début de la session

1. **Invendables** (dons, alimentation animale, destruction) : proposition → action « Sortir en invendable » sur un lot **bloqué ou périmé** de la plateforme, réservée à `qualite` et `admin`, avec une **destination obligatoire** (don à une association, alimentation animale, destruction) et un motif ; mouvement de sortie de tout le stock restant, lot passé au statut `détruit` (définitif). Valorisation (pour la démarque) en phase 8.
2. **Préparation en deux temps** : proposition → (1) « Préparer » : lots proposés en FEFO, ajustables (justification obligatoire hors FEFO, comme en production), commande en `en_preparation`, **sans mouvement de stock** ; (2) « Expédier » : transporteur + température, contrôle de stock refait, mouvements d'expédition, palettes SSCC, bon de livraison, commande `expediee`.
3. **Expédition directe de la phase 5** (`POST /api/ventes/shipments/`) : proposition → la **retirer** (comme la déclaration directe de fabrication en phase 6) ; toute expédition passe par une commande client. La liste des expéditions reste consultable.

## 4. Conception proposée

### Modèles (`ventes/models.py`)

| Modèle | Champs principaux |
| --- | --- |
| `Shipment` (bon de livraison) | numéro `BL-AAAA-NNNNN`, commande (une expédition par commande, puisqu'il n'y a pas de reliquat), statut (`preparee` → `expediee`, ou `refusee`), préparée par / le, transporteur (texte), température au chargement, expédiée par / le, motif de refus |
| `ShipmentLine` (ligne préparée) | expédition, ligne de commande, lot, emplacement, quantité, justification hors FEFO, mouvement de stock créé à l'expédition |
| `Pallet` | expédition, SSCC (18 chiffres, unique), rang |
| `PalletLine` | palette, ligne préparée, quantité |

### Services (`ventes/shipping.py`, nouveau module)

- `min_expiry_for(customer, article, delivery_date)` : date limite minimale (décision 6).
- `picking_proposal(order)` : pour chaque ligne, `fefo_plan(article, site PFN, quantité, min_expiry_date=…)` ; lots pré-remplis, manquant affiché.
- `prepare_order(order, lines, user)` : contrôle FEFO (justification hors FEFO), DLC minimale, MDD, statut des lots ; crée `Shipment` + `ShipmentLine` ; commande → `en_preparation`.
- `ship_order(shipment, carrier, temperature, user)` : si température > 4 °C → `refusee`, lots bloqués (`block_lot`), alerte (`raise_alert`, type à ajouter) ; sinon `record_shipment` pour chaque ligne (adapter la DLC minimale à la **date de livraison demandée**), découpage en palettes de 720 u, SSCC, commande → `expediee`.
- `sscc(serial)` : extension `0` + préfixe GS1 fictif (7 chiffres, ex. `3770000`) + numéro de série (compteur `DocumentSequence` « SSCC », 9 chiffres) + clé de contrôle modulo 10 (pondérations 3/1 depuis la droite).
- `service_rate(customer=None, start, end)` : par ligne, quantité expédiée à temps ÷ quantité commandée, hors commandes annulées.
- `dispose_unsold(lot, destination, reason, user)` : invendables (voir point 3.1) ; nouveaux types de mouvement `don`, `alimentation_animale` (la destruction existe déjà).

### API et écrans

- `/api/ventes/orders/{id}/picking-proposal/` (GET), `/prepare/` (POST), `/api/ventes/shipments/{id}/ship/` (POST), `/api/ventes/service-rate/?start=…&end=…`, action invendables sur `/api/stocks/lots/{id}/dispose/`.
- Écrans React :
  - fiche commande client : boutons **Préparer** puis **Expédier** (magasinier) ;
  - page de préparation (sur le modèle de `DeclarationPage.tsx`) ;
  - liste des bons de livraison et fiche BL avec palettes, SSCC et étiquette imprimable ;
  - page **Taux de service** par enseigne (badge rouge sous 98,5 %) ;
  - action « Sortir en invendable » sur la fiche lot (qualité).

### Données de démonstration (`ventes/demo_data.py` ou `ventes/demo_shipping.py`)

- Déclarer d'abord une partie des OF de produits finis de la phase 6 (ou libérer des lots existants) pour avoir du stock à `PFN-FRAIS-A`.
- Préparer et expédier plusieurs commandes de la démo 7a : une complète et à l'heure, une en rupture partielle, une **refusée pour température** (5,8 °C), une expédiée en retard.
- Une sortie d'invendable (ex. le lot d'œufs périmé vers la destruction, un lot proche de la DLC en don).

### Tests à écrire (au minimum)

DLC minimale à la date de livraison ; proposition FEFO qui exclut les lots trop courts pour l'enseigne ; justification hors FEFO ; rupture sans reliquat ; température > 4 °C → refus + blocage + alerte ; découpage en palettes de 720 ; SSCC à 18 chiffres avec bonne clé de contrôle ; taux de service (complet, partiel, en retard) ; invendables (destination obligatoire, lot détruit, mouvement) ; droits (magasinier prépare et expédie, commercial non) ; traçabilité aval retrouvant l'expédition ; parcours complet par l'API ; données de démo relançables.

## 5. Fin de la partie 7b (liste de contrôle)

- [ ] Tests back-end et front-end verts, lint propre, migrations à jour.
- [ ] Vérification dans le navigateur (avec le compte `test-verif` pour agir).
- [ ] `docs/decisions.md` : section « Phase 7b » + mise à jour des points en suspens.
- [ ] `README.md` : parcours de préparation et d'expédition.
- [ ] `CLAUDE.md` : phase 7 → « Terminée ».
- [ ] Ce fichier : remplacer par le plan de la **phase 8 (pilotage)**.
- [ ] Commits, envoi de la branche, pull request créée et fusionnée par Nicolas.

## 6. Repartir d'une base de démonstration neuve (si besoin)

⚠️ Efface toutes les données locales, y compris le compte administrateur. À ne faire qu'avec l'accord de Nicolas.

```powershell
docker compose down -v
```

```powershell
docker compose up -d
```

```powershell
docker compose exec backend python manage.py createsuperuser
```

```powershell
docker compose exec backend python manage.py charger_donnees_demo
```
