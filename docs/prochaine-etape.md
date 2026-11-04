# Prochaine étape : phase 8 – Pilotage

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md`, `docs/decisions.md` et la section 7 (« Indicateurs ») de `docs/fiche-entreprise.md`.

## 1. Où en est le projet (fin de la phase 7)

- Phases 1 à 7 terminées. La partie 7b (préparation FEFO, bons de livraison `BL-`, palettes SSCC, expédition avec contrôle de température, taux de service, invendables) est sur la branche `phase-7b-expedition`, à fusionner par Nicolas.
- Tests : 360 environ côté back-end (pytest) et 39 côté front-end (Vitest), tous verts.
- Existant utile pour la phase 8 :
  - `ventes/shipping.py` : `service_rate(start, end, customer)` (taux de service complet, déjà calculé) ;
  - `production/orders.py` : `yield_report(order)` (rendement matière) ;
  - mouvements de stock typés (`stocks/choices.py`) : `expedition`, `consommation`, `destruction`, `don`, `alimentation_animale`, `destruction_invendable`, `inventaire`… ;
  - tarifs de vente datés (`ventes.SalePrice`), tarifs d'achat datés (`achats.SupplierPrice`) ;
  - lignes de réception avec leur conformité (achats) ;
  - rappels avec la durée de calcul mesurée (`qualite`).
  - PostgreSQL accessible depuis le PC (`localhost:5432`, identifiants du `.env`) pour Excel et Power BI.

## 2. Indicateurs de la fiche entreprise

| Indicateur | Définition | Objectif | Source dans l'ERP |
| --- | --- | --- | --- |
| Taux de service | Livré complet et à l'heure / commandé | ≥ 98,5 % | `service_rate` (déjà fait) |
| Démarque | Valeur détruite ou déclassée / CA | ≤ 1,5 % | mouvements de destruction et d'invendables × prix ; CA = expéditions × prix de vente |
| Couverture PF | Stock / ventes moyennes journalières | 2 à 4 j | stock libéré PF ÷ expéditions moyennes |
| Couverture matières | Stock / consommation moyenne journalière | 5 à 10 j | stock MP ÷ consommations moyennes |
| Rendement matière | Produit / théorique | ≥ 96 % | `yield_report` par OF |
| TRS | Taux de rendement synthétique des lignes | ≥ 70 % | **pas de données** (temps d'arrêt, cadences réelles) : à décider |
| Fiabilité prévisions | 1 − écart absolu / ventes réelles | ≥ 80 % à S-1 | **pas de prévisions** dans l'ERP : à décider |
| Conformité réception | Livraisons conformes / total | ≥ 97 % | lignes de réception |
| Délai de traçabilité | Durée d'un rappel complet | ≤ 5 min | mesure du calcul d'impact |

## 3. Points à faire valider au début de la session

1. **TRS et fiabilité des prévisions** : proposition → les afficher « non disponibles » (sans données de temps d'arrêt ni de prévisions), plutôt que d'inventer des chiffres ; ou ajouter une saisie simple (arrêts par ligne, prévisions hebdomadaires) dans une phase complémentaire.
2. **Valorisation de la démarque** : proposition → produits finis au prix de vente moyen en vigueur (Brévanne), matières au prix d'achat en vigueur à la date du mouvement.
3. **Où calculer** : proposition → des **vues SQL** PostgreSQL en lecture seule (schéma `bi`, une migration Django), utilisées à la fois par l'API des tableaux de bord et par Power BI / Power Query. Un utilisateur PostgreSQL en **lecture seule** pour Power BI.
4. **Données de démonstration plus riches** : le stock de produits finis est petit et les commandes EDI de démo sont presque toutes en rupture (taux de service très bas). Proposition → générer un historique de quelques semaines (réceptions, OF déclarés, expéditions) pour des indicateurs réalistes, via un script dans `data/`.

## 4. Conception proposée (à préciser)

- App Django `pilotage` : `pilotage/indicators.py` (calculs), API `/api/pilotage/indicators/?start=…&end=…&site=…`.
- Écran React **Tableau de bord** : une tuile par indicateur (valeur, objectif, rouge/vert), évolution par semaine, filtres période / site / enseigne.
- Dossier `bi/` : requêtes Power Query (`.pq`), documentation de chaque indicateur (définition, source, formule), modèle Power BI si possible.
- Tests : chaque indicateur sur un petit jeu de données dont le résultat est connu ; droits (tous les rôles consultent, `direction` en particulier).

## 5. Fin de la phase 8 (liste de contrôle)

- [ ] Tests back-end et front-end verts, lint propre, migrations à jour.
- [ ] Vérification dans le navigateur (avec le compte `test-verif`, à l'adresse `127.0.0.1:5173` pour ne pas toucher à la session de Nicolas sur `localhost`).
- [ ] Connexion testée depuis Excel (Power Query) ou Power BI Desktop.
- [ ] `docs/decisions.md` : section « Phase 8 » + mise à jour des points en suspens.
- [ ] `README.md` : tableau de bord et connexion Power BI pas à pas.
- [ ] `CLAUDE.md` : phase 8 → « Terminée ».
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
