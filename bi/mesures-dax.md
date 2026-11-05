# Modèle Power BI : relations et mesures DAX

Ce fichier sert à construire le rapport Power BI des indicateurs. Le pas à pas complet est dans le [README](../README.md#connexion-power-bi--excel). Les tables portent le nom des requêtes de [`power-query/`](power-query/) (`fact_service`, `dim_date`…) : garde ces noms, les formules ci-dessous les utilisent.

Les mesures reproduisent exactement les calculs du tableau de bord de l'application (`backend/pilotage/indicators.py`). Sur la même période, les chiffres doivent être identiques : c'est la meilleure façon de vérifier le modèle.

## 1. Relations à créer (vue Modèle)

Toutes de type « un à plusieurs », la dimension du côté « un », filtre dans un seul sens.

| Dimension (un) | Table de faits (plusieurs) |
| --- | --- |
| `dim_date[date]` | `fact_stock_movement[date]`, `fact_stock_daily[date]`, `fact_sales[date]`, `fact_reception[date]`, `fact_production_yield[date]`, `fact_recall[date]` |
| `dim_date[date]` | `fact_service[requested_delivery_date]` (le taux de service se compte sur la livraison demandée) |
| `dim_article[article_id]` | `fact_stock_movement`, `fact_stock_daily`, `fact_sales`, `fact_reception`, `fact_production_yield` (colonne `article_id`) |
| `dim_customer[customer_id]` | `fact_sales[customer_id]`, `fact_service[customer_id]` |
| `dim_site[site_id]` | `fact_stock_movement`, `fact_stock_daily`, `fact_reception`, `fact_production_yield` (colonne `site_id`) |

Puis : clic droit sur `dim_date` → **Marquer comme table de dates**, colonne `date`.

## 2. Mesures

Créer une table vide nommée `Mesures` (Accueil → Entrer des données → OK), puis, pour chaque mesure : clic droit sur `Mesures` → **Nouvelle mesure**, coller la formule. Format conseillé entre parenthèses.

### Taux de service (pourcentage, 1 décimale)

```dax
Taux de service =
DIVIDE (
    CALCULATE ( SUM ( fact_service[delivered_on_time] ), fact_service[is_counted] = TRUE () ),
    CALCULATE ( SUM ( fact_service[ordered] ), fact_service[is_counted] = TRUE () )
)
```

### Chiffre d'affaires et démarque

```dax
CA = SUM ( fact_sales[amount] )
```

```dax
Démarque (€) =
- CALCULATE ( SUM ( fact_stock_movement[value] ), fact_stock_movement[is_markdown] = TRUE () )
```

```dax
Démarque (% du CA) = DIVIDE ( [Démarque (€)], [CA] )
```

### Couvertures (nombre décimal, 1 décimale, en jours)

Stock disponible (lots libérés ou en quarantaine) le dernier jour de la période, divisé par les sorties moyennes par jour. Comme dans l'application, la période s'arrête à aujourd'hui.

```dax
Couverture produits finis (j) =
VAR LastDay = MIN ( MAX ( dim_date[date] ), TODAY () )
VAR FirstDay = MIN ( dim_date[date] )
VAR Days = DATEDIFF ( FirstDay, LastDay, DAY ) + 1
VAR Stock =
    CALCULATE (
        SUM ( fact_stock_daily[value] ),
        dim_date[date] = LastDay,
        fact_stock_daily[lot_status] IN { "libere", "quarantaine" },
        dim_article[article_type] = "PF"
    )
VAR Outflow =
    - CALCULATE (
        SUM ( fact_stock_movement[value] ),
        dim_date[date] >= FirstDay && dim_date[date] <= LastDay,
        fact_stock_movement[movement_type] = "expedition",
        dim_article[article_type] = "PF"
    )
RETURN
    DIVIDE ( Stock, DIVIDE ( Outflow, Days ) )
```

```dax
Couverture matières (j) =
VAR LastDay = MIN ( MAX ( dim_date[date] ), TODAY () )
VAR FirstDay = MIN ( dim_date[date] )
VAR Days = DATEDIFF ( FirstDay, LastDay, DAY ) + 1
VAR Stock =
    CALCULATE (
        SUM ( fact_stock_daily[value] ),
        dim_date[date] = LastDay,
        fact_stock_daily[lot_status] IN { "libere", "quarantaine" },
        dim_article[article_type] = "MP"
    )
VAR Outflow =
    - CALCULATE (
        SUM ( fact_stock_movement[value] ),
        dim_date[date] >= FirstDay && dim_date[date] <= LastDay,
        fact_stock_movement[movement_type] = "consommation",
        dim_article[article_type] = "MP"
    )
RETURN
    DIVIDE ( Stock, DIVIDE ( Outflow, Days ) )
```

### Rendement matière (pourcentage, 1 décimale)

```dax
Rendement matière =
DIVIDE ( SUM ( fact_production_yield[theoretical_mass] ), SUM ( fact_production_yield[actual_mass] ) )
```

```dax
OF sous 96 % = CALCULATE ( COUNTROWS ( fact_production_yield ), fact_production_yield[yield_pct] < 96 )
```

### Conformité réception (pourcentage, 1 décimale)

```dax
Conformité réception =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_reception ), fact_reception[is_compliant] = TRUE () ),
    COUNTROWS ( fact_reception )
)
```

### Délai de traçabilité (nombre entier, en millisecondes)

Durée des rappels lancés. Le « rappel à blanc » mesuré à chaque ouverture du tableau de bord n'existe que dans l'application.

```dax
Délai de traçabilité max (ms) = MAX ( fact_recall[duration_ms] )
```

### Objectifs (pour les couleurs)

```dax
Taux de service – objectif atteint = IF ( [Taux de service] >= 0.985, 1, 0 )
```

Pour colorer une valeur : sélectionner le visuel → Format → Valeurs → couleur de police → **fx** → « Règles » (vert si ≥ objectif, rouge sinon). Objectifs de la fiche entreprise : taux de service ≥ 98,5 %, démarque ≤ 1,5 %, couverture produits finis 2 à 4 j, couverture matières 5 à 10 j, rendement ≥ 96 %, conformité réception ≥ 97 %.

## 3. Pages proposées

1. **Synthèse** : une carte par mesure, un segment (slicer) sur `dim_date[date]` (entre deux dates) et un sur `dim_customer[name]`.
2. **Évolution** : matrice avec `dim_date[week_label]` en colonnes et les mesures en valeurs.
3. **Ventes et service** : taux de service et CA par enseigne (`dim_customer[name]`), par marque (`dim_article[brand]`).
4. **Démarque** : démarque (€) par article et par type de mouvement (`fact_stock_movement[movement_type]`).
