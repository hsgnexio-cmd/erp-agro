# bi – Pilotage et analyse

Ce dossier documente les données de pilotage de l'ERP. Les requêtes Power Query et le modèle Power BI arriveront en phase 8b.

## Le schéma `bi` de PostgreSQL

Les indicateurs sont calculés dans des **vues SQL**, c'est-à-dire des tables « virtuelles » en lecture seule, recalculées à chaque lecture. Elles sont regroupées dans le schéma `bi` de la base. Le tableau de bord de l'application et Power BI lisent ces mêmes vues : les chiffres sont donc identiques partout.

- Code SQL : [`backend/pilotage/sql/bi_views.sql`](../backend/pilotage/sql/bi_views.sql), créé par la migration `pilotage/0001_vues_bi`.
- Calcul des indicateurs du tableau de bord : [`backend/pilotage/indicators.py`](../backend/pilotage/indicators.py).

Les dates sont en heure de Paris. Les montants sont en euros HT.

### Dimensions (« qui, quoi, où, quand »)

| Vue | Une ligne par… | Colonnes utiles |
| --- | --- | --- |
| `bi.dim_date` | jour (de début de l'année dernière à J+60) | `date`, `week_start`, `week_label` (ex. 2026-S45), `month`, `day_of_week` |
| `bi.dim_site` | site | `site_id`, `code` (NAN, REN, PFN, MPE), `name`, `site_type` |
| `bi.dim_customer` | enseigne | `customer_id`, `code` (ENS1…ENS6), `name`, `min_remaining_shelf_life_pct` |
| `bi.dim_article` | article | `article_id`, `code`, `article_type` (MP, SF, PF, EM), `family_code`, `factory_code`, `brand` (Brévanne ou MDD ENSx), `unit` |

### Faits (ce qui s'est passé)

| Vue | Une ligne par… | Sert à |
| --- | --- | --- |
| `bi.fact_stock_movement` | mouvement de stock, valorisé (`value`) ; `is_markdown` = destruction, don, alimentation animale, destruction d'invendable | démarque, couvertures (sorties) |
| `bi.fact_stock_daily` | jour × article × site × statut du lot ce jour-là : stock de fin de journée | couvertures |
| `bi.fact_sales` | ligne expédiée : quantité, prix, montant (`amount`) | chiffre d'affaires |
| `bi.fact_service` | commande client : commandé, livré à l'heure, en retard, manquant ; `is_counted` = faux pour une commande encore dans les temps | taux de service |
| `bi.fact_reception` | ligne de réception : `is_compliant`, motifs | conformité réception |
| `bi.fact_production_yield` | OF terminé : masse théorique, masse réelle, `yield_pct` | rendement matière |
| `bi.fact_recall` | rappel lancé : durée du calcul (`duration_ms`), lots bloqués, clients | délai de traçabilité |

### Valorisation

Une fonction SQL donne le prix d'un article à une date : `bi.unit_value(article_id, fournisseur_id, date)`.

- **Produit fini** : prix de vente moyen des enseignes, en vigueur à la date.
- **Matière ou emballage** : prix d'achat en vigueur à la date, chez le fournisseur du lot (sinon la moyenne des fournisseurs).
- **Semi-fini** : coût de sa nomenclature (matières au prix d'achat, pertes comprises).

## Les indicateurs

| Indicateur | Formule (sur les vues) | Objectif |
| --- | --- | --- |
| Taux de service | `sum(delivered_on_time) / sum(ordered)` de `fact_service`, commandes comptées (`is_counted`) dont la livraison demandée tombe dans la période | ≥ 98,5 % |
| Démarque | `-sum(value)` des mouvements `is_markdown` ÷ `sum(amount)` de `fact_sales` | ≤ 1,5 % |
| Couverture produits finis | valeur du stock PF libéré ou en quarantaine à la date de fin (`fact_stock_daily`) ÷ (valeur des expéditions de la période ÷ nombre de jours) | 2 à 4 jours |
| Couverture matières | idem pour les matières premières, avec les consommations | 5 à 10 jours |
| Rendement matière | `sum(theoretical_mass) / sum(actual_mass)` de `fact_production_yield` | ≥ 96 % |
| Conformité réception | lignes `is_compliant` ÷ lignes de `fact_reception` | ≥ 97 % |
| Délai de traçabilité | rappel « à blanc » mesuré par l'application ; durée des vrais rappels dans `fact_recall` | ≤ 5 min |
| TRS | non disponible : pas de données d'arrêts de ligne | ≥ 70 % |
| Fiabilité des prévisions | non disponible : pas de prévisions dans l'ERP | ≥ 80 % |

Exemple de requête pour le taux de service par semaine :

```sql
SELECT date_trunc('week', requested_delivery_date)::date AS semaine,
       round(sum(delivered_on_time) / sum(ordered) * 100, 1) AS taux_de_service
  FROM bi.fact_service
 WHERE is_counted
 GROUP BY 1
 ORDER BY 1;
```
