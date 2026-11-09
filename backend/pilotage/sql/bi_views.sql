-- Schéma « bi » : vues en lecture seule pour le pilotage (phase 8).
--
-- Ces vues sont la source unique des indicateurs : l'API du tableau de bord les interroge,
-- et Power BI / Power Query s'y connectent directement. Les noms suivent la convention du
-- code (anglais) ; leur description en français est dans bi/README.md.
--
-- Dates : toujours en heure de Paris (règle de la section 6 de CLAUDE.md).
-- Valorisation (décision de la phase 8) :
--   - produit fini : prix de vente moyen des enseignes en vigueur à la date ;
--   - matière et emballage : prix d'achat en vigueur à la date (chez le fournisseur du lot,
--     sinon moyenne des fournisseurs) ;
--   - semi-fini : coût de sa nomenclature (matières au prix d'achat, pertes comprises).

CREATE SCHEMA IF NOT EXISTS bi;

-- --- Fonctions de valorisation ----------------------------------------------------------
-- Elles lisent les tarifs avec les droits du propriétaire (SECURITY DEFINER) : l'utilisateur
-- Power BI, qui n'a accès qu'au schéma bi, peut ainsi les appeler sans voir les tables.

CREATE OR REPLACE FUNCTION bi.local_date(moment timestamptz) RETURNS date
LANGUAGE sql IMMUTABLE AS $$
    SELECT (moment AT TIME ZONE 'Europe/Paris')::date
$$;

CREATE OR REPLACE FUNCTION bi.purchase_price(p_article bigint, p_supplier bigint, p_date date)
RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, bi AS $$
    SELECT COALESCE(
        (SELECT p.unit_price
           FROM achats_supplierprice p
           JOIN referentiel_supplierarticle sa ON sa.id = p.supplier_article_id
          WHERE sa.article_id = p_article AND sa.supplier_id = p_supplier
            AND p.valid_from <= p_date AND (p.valid_to IS NULL OR p.valid_to >= p_date)
          ORDER BY p.valid_from DESC LIMIT 1),
        (SELECT avg(p.unit_price)
           FROM achats_supplierprice p
           JOIN referentiel_supplierarticle sa ON sa.id = p.supplier_article_id
          WHERE sa.article_id = p_article
            AND p.valid_from <= p_date AND (p.valid_to IS NULL OR p.valid_to >= p_date))
    )
$$;

CREATE OR REPLACE FUNCTION bi.sale_price(p_article bigint, p_date date)
RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, bi AS $$
    SELECT avg(p.unit_price)
      FROM ventes_saleprice p
     WHERE p.article_id = p_article
       AND p.valid_from <= p_date AND (p.valid_to IS NULL OR p.valid_to >= p_date)
$$;

-- Coût d'un semi-fini : ses matières (prix d'achat) pour une unité, pertes comprises
CREATE OR REPLACE FUNCTION bi.bom_cost(p_article bigint, p_date date)
RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, bi AS $$
    SELECT sum(
               l.quantity / (1 - l.loss_rate / 100)
               * bi.purchase_price(l.component_id, NULL::bigint, p_date)
           ) / max(b.base_quantity)
      FROM referentiel_billofmaterials b
      JOIN referentiel_bomline l ON l.bom_id = b.id
     WHERE b.article_id = p_article
$$;

CREATE OR REPLACE FUNCTION bi.unit_value(p_article bigint, p_supplier bigint, p_date date)
RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, bi AS $$
    SELECT CASE a.article_type
               WHEN 'PF' THEN bi.sale_price(a.id, p_date)
               WHEN 'SF' THEN bi.bom_cost(a.id, p_date)
               ELSE bi.purchase_price(a.id, p_supplier, p_date)
           END
      FROM referentiel_article a
     WHERE a.id = p_article
$$;

-- --- Dimensions ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW bi.dim_date AS
SELECT d::date AS date,
       extract(isoyear FROM d)::int AS iso_year,
       extract(week FROM d)::int AS iso_week,
       date_trunc('week', d)::date AS week_start,
       to_char(d, 'IYYY-"S"IW') AS week_label,
       extract(year FROM d)::int AS year,
       extract(month FROM d)::int AS month,
       extract(isodow FROM d)::int AS day_of_week
  FROM generate_series(
           date_trunc('year', current_date) - interval '1 year',
           current_date + interval '60 days',
           interval '1 day'
       ) AS d;

CREATE OR REPLACE VIEW bi.dim_site AS
SELECT id AS site_id, code, name, site_type, city, active
  FROM referentiel_site;

CREATE OR REPLACE VIEW bi.dim_customer AS
SELECT id AS customer_id, code, name, customer_type, sells_brand, sells_private_label,
       min_remaining_shelf_life_pct, active
  FROM referentiel_customer;

CREATE OR REPLACE VIEW bi.dim_article AS
SELECT a.id AS article_id,
       a.code,
       a.name,
       a.article_type,
       CASE a.article_type
           WHEN 'MP' THEN 'Matière première'
           WHEN 'SF' THEN 'Semi-fini'
           WHEN 'PF' THEN 'Produit fini'
           WHEN 'EM' THEN 'Emballage'
       END AS article_type_label,
       a.unit,
       c.code AS category_code,
       f.code AS family_code,
       f.name AS family_name,
       s.code AS factory_code,
       CASE WHEN a.article_type <> 'PF' THEN NULL
            WHEN a.brand_customer_id IS NULL THEN 'Brévanne'
            ELSE 'MDD ' || bc.code END AS brand,
       a.format_size,
       a.shelf_life_days,
       a.active
  FROM referentiel_article a
  LEFT JOIN referentiel_materialcategory c ON c.id = a.category_id
  LEFT JOIN referentiel_recipe r ON r.id = a.recipe_id
  LEFT JOIN referentiel_productfamily f ON f.id = r.family_id
  LEFT JOIN referentiel_site s ON s.id = f.site_id
  LEFT JOIN referentiel_customer bc ON bc.id = a.brand_customer_id;

-- --- Faits ------------------------------------------------------------------------------

-- Tous les mouvements de stock, valorisés. Démarque = destructions et invendables.
CREATE OR REPLACE VIEW bi.fact_stock_movement AS
SELECT m.id AS movement_id,
       bi.local_date(m.created_at) AS date,
       m.created_at,
       m.movement_type,
       m.movement_type IN ('destruction', 'don', 'alimentation_animale',
                           'destruction_invendable') AS is_markdown,
       l.id AS lot_id,
       l.number AS lot_number,
       l.article_id,
       loc.site_id,
       loc.code AS location_code,
       m.quantity,
       bi.unit_value(l.article_id, l.supplier_id, bi.local_date(m.created_at)) AS unit_value,
       m.quantity * bi.unit_value(l.article_id, l.supplier_id, bi.local_date(m.created_at))
           AS value,
       m.reference,
       m.reason
  FROM stocks_stockmovement m
  JOIN stocks_lot l ON l.id = m.lot_id
  JOIN referentiel_location loc ON loc.id = m.location_id;

-- Ventes : lignes expédiées, au prix de la commande (tarif en vigueur sinon)
CREATE OR REPLACE VIEW bi.fact_sales AS
SELECT sl.id AS shipment_line_id,
       bi.local_date(s.shipped_at) AS date,
       s.number AS shipment_number,
       o.number AS order_number,
       o.customer_id,
       w.code AS warehouse_code,
       ol.article_id,
       sl.lot_id,
       sl.quantity,
       COALESCE(ol.unit_price, bi.sale_price(ol.article_id, bi.local_date(s.shipped_at)))
           AS unit_price,
       sl.quantity
           * COALESCE(ol.unit_price, bi.sale_price(ol.article_id, bi.local_date(s.shipped_at)))
           AS amount
  FROM ventes_shipmentline sl
  JOIN ventes_shipment s ON s.id = sl.shipment_id AND s.status = 'expediee'
  JOIN ventes_customerorderline ol ON ol.id = sl.order_line_id
  JOIN ventes_customerorder o ON o.id = ol.order_id
  JOIN referentiel_customerwarehouse w ON w.id = o.warehouse_id;

-- Taux de service, commande par commande (même règle que ventes.shipping.service_rate) :
-- « à l'heure » = expédiée au plus tard la veille de la livraison demandée ; une commande
-- non expédiée mais encore dans les temps est « en cours » et n'est pas comptée.
CREATE OR REPLACE VIEW bi.fact_service AS
WITH shipped AS (
    SELECT DISTINCT ON (s.order_id) s.order_id, s.id, bi.local_date(s.shipped_at) AS shipped_date
      FROM ventes_shipment s
     WHERE s.status = 'expediee'
     ORDER BY s.order_id, s.shipped_at
),
lines AS (
    SELECT ol.order_id,
           sum(ol.quantity) AS ordered,
           sum(LEAST(ol.quantity, COALESCE(d.delivered, 0))) AS delivered
      FROM ventes_customerorderline ol
      LEFT JOIN shipped sh ON sh.order_id = ol.order_id
      LEFT JOIN LATERAL (
          SELECT sum(sl.quantity) AS delivered
            FROM ventes_shipmentline sl
           WHERE sl.shipment_id = sh.id AND sl.order_line_id = ol.id
      ) d ON true
     GROUP BY ol.order_id
)
SELECT o.id AS order_id,
       o.number AS order_number,
       o.customer_id,
       o.requested_delivery_date,
       o.requested_delivery_date - 1 AS on_time_limit,
       sh.shipped_date,
       (sh.order_id IS NOT NULL OR current_date > o.requested_delivery_date - 1) AS is_counted,
       (sh.shipped_date IS NOT NULL AND sh.shipped_date <= o.requested_delivery_date - 1)
           AS is_on_time,
       lines.ordered,
       lines.delivered,
       CASE WHEN sh.shipped_date <= o.requested_delivery_date - 1 THEN lines.delivered
            ELSE 0 END AS delivered_on_time,
       CASE WHEN sh.shipped_date > o.requested_delivery_date - 1 THEN lines.delivered
            ELSE 0 END AS delivered_late,
       lines.ordered - lines.delivered AS missing
  FROM ventes_customerorder o
  JOIN lines ON lines.order_id = o.id
  LEFT JOIN shipped sh ON sh.order_id = o.id
 WHERE o.status <> 'annulee';

-- Conformité des réceptions, ligne par ligne
CREATE OR REPLACE VIEW bi.fact_reception AS
SELECT rl.id AS reception_line_id,
       bi.local_date(r.received_at) AS date,
       r.number AS reception_number,
       po.supplier_id,
       loc.site_id,
       pol.article_id,
       rl.quantity,
       rl.is_compliant,
       rl.non_compliance_reasons
  FROM achats_receptionline rl
  JOIN achats_reception r ON r.id = rl.reception_id
  JOIN achats_purchaseorder po ON po.id = r.order_id
  JOIN achats_purchaseorderline pol ON pol.id = rl.order_line_id
  JOIN referentiel_location loc ON loc.id = r.location_id;

-- Rendement matière des OF terminés (même règle que production.orders.yield_report) :
-- théorique ÷ réel, sur les composants en kg et en litres, pertes de nomenclature comprises.
CREATE OR REPLACE VIEW bi.fact_production_yield AS
WITH produced AS (
    SELECT d.order_id, sum(l.initial_quantity) AS quantity
      FROM production_productiondeclaration d
      JOIN stocks_lot l ON l.id = d.lot_id
     GROUP BY d.order_id
),
theoretical AS (
    SELECT o.id AS order_id, bl.component_id,
           round(bl.quantity * p.quantity / b.base_quantity / (1 - bl.loss_rate / 100), 3)
               AS quantity
      FROM production_productionorder o
      JOIN produced p ON p.order_id = o.id
      JOIN referentiel_billofmaterials b ON b.article_id = o.article_id
      JOIN referentiel_bomline bl ON bl.bom_id = b.id AND bl.unit IN ('kg', 'l')
),
actual AS (
    SELECT d.order_id, cl.article_id AS component_id, -sum(m.quantity) AS quantity
      FROM production_productiondeclaration d
      JOIN stocks_stockmovement m
        ON m.produced_lot_id = d.lot_id AND m.movement_type = 'consommation'
      JOIN stocks_lot cl ON cl.id = m.lot_id
     GROUP BY d.order_id, cl.article_id
),
masses AS (
    SELECT t.order_id, sum(t.quantity) AS theoretical, sum(COALESCE(a.quantity, 0)) AS actual
      FROM theoretical t
      LEFT JOIN actual a ON a.order_id = t.order_id AND a.component_id = t.component_id
     GROUP BY t.order_id
)
SELECT o.id AS order_id,
       o.number AS order_number,
       bi.local_date(o.closed_at) AS date,
       o.site_id,
       pl.code AS line_code,
       o.article_id,
       p.quantity AS produced,
       m.theoretical AS theoretical_mass,
       m.actual AS actual_mass,
       CASE WHEN m.actual > 0 THEN round(m.theoretical / m.actual * 100, 1) END AS yield_pct
  FROM production_productionorder o
  JOIN produced p ON p.order_id = o.id
  JOIN masses m ON m.order_id = o.id
  LEFT JOIN referentiel_productionline pl ON pl.id = o.line_id
 WHERE o.status = 'termine';

-- Stock de fin de journée par article, site et statut du lot ce jour-là (pour les couvertures).
-- Le statut d'un jour passé est retrouvé dans le journal des statuts (LotStatusChange).
CREATE OR REPLACE VIEW bi.fact_stock_daily AS
WITH daily AS (
    SELECT m.lot_id, loc.site_id, bi.local_date(m.created_at) AS day, sum(m.quantity) AS quantity
      FROM stocks_stockmovement m
      JOIN referentiel_location loc ON loc.id = m.location_id
     GROUP BY m.lot_id, loc.site_id, bi.local_date(m.created_at)
),
grid AS (
    SELECT s.lot_id, s.site_id, g.day::date AS day
      FROM (SELECT lot_id, site_id, min(day) AS first_day FROM daily GROUP BY lot_id, site_id) s
     CROSS JOIN LATERAL generate_series(s.first_day, current_date, interval '1 day') AS g(day)
),
balances AS (
    SELECT grid.lot_id, grid.site_id, grid.day,
           sum(COALESCE(daily.quantity, 0)) OVER (
               PARTITION BY grid.lot_id, grid.site_id ORDER BY grid.day
           ) AS quantity
      FROM grid
      LEFT JOIN daily
        ON daily.lot_id = grid.lot_id AND daily.site_id = grid.site_id AND daily.day = grid.day
),
changes AS (
    SELECT c.lot_id, bi.local_date(c.changed_at) AS from_day, c.to_status AS status,
           lead(bi.local_date(c.changed_at)) OVER (
               PARTITION BY c.lot_id ORDER BY c.changed_at, c.id
           ) AS next_day
      FROM stocks_lotstatuschange c
),
periods AS (
    SELECT lot_id, from_day, status, next_day FROM changes
    UNION ALL
    -- Statut d'origine, jusqu'au premier changement
    SELECT l.id, bi.local_date(l.created_at),
           COALESCE(first.from_status, l.status),
           bi.local_date(first.changed_at)
      FROM stocks_lot l
      LEFT JOIN LATERAL (
          SELECT c.from_status, c.changed_at
            FROM stocks_lotstatuschange c
           WHERE c.lot_id = l.id
           ORDER BY c.changed_at, c.id
           LIMIT 1
      ) first ON true
)
SELECT b.day AS date,
       l.article_id,
       b.site_id,
       p.status AS lot_status,
       sum(b.quantity) AS quantity,
       sum(b.quantity) * bi.unit_value(l.article_id, NULL, b.day) AS value
  FROM balances b
  JOIN stocks_lot l ON l.id = b.lot_id
  JOIN periods p
    ON p.lot_id = b.lot_id AND p.from_day <= b.day AND (p.next_day IS NULL OR p.next_day > b.day)
 WHERE b.quantity <> 0
 GROUP BY b.day, l.article_id, b.site_id, p.status;

-- Rappels lancés, avec la durée du calcul d'impact (délai de traçabilité)
CREATE OR REPLACE VIEW bi.fact_recall AS
SELECT r.id AS recall_id,
       r.number AS recall_number,
       bi.local_date(r.created_at) AS date,
       l.number AS origin_lot_number,
       l.article_id AS origin_article_id,
       (r.snapshot ->> 'duration_ms')::int AS duration_ms,
       jsonb_array_length(COALESCE(r.snapshot -> 'blocked_lots', '[]'::jsonb)) AS blocked_lots,
       jsonb_array_length(COALESCE(r.snapshot -> 'customers', '[]'::jsonb)) AS customers
  FROM qualite_productrecall r
  JOIN stocks_lot l ON l.id = r.origin_lot_id;

-- --- Prévisions de vente (phase 9a) -----------------------------------------------------

-- Lignes de toutes les versions de prévision figées (produit × enseigne × semaine)
CREATE OR REPLACE VIEW bi.fact_forecast AS
SELECT l.id AS forecast_line_id,
       v.number AS version_number,
       bi.local_date(v.created_at) AS version_date,
       v.source AS version_source,
       l.week AS week_start,
       to_char(l.week, 'IYYY-"S"IW') AS week_label,
       l.customer_id,
       l.article_id,
       l.base_quantity,
       l.promo_coefficient,
       l.adjustment_id IS NOT NULL AS is_adjusted,
       l.quantity
  FROM previsions_forecastline l
  JOIN previsions_forecastversion v ON v.id = l.version_id;

-- Fiabilité à S-1 (même règle que previsions.forecast.week_accuracy) : pour chaque semaine,
-- la dernière version figée avant son lundi (heure de Paris) et qui la couvre, comparée aux
-- quantités commandées (commandes non annulées, par semaine de livraison demandée).
-- Fiabilité = 1 − sum(abs_error) ÷ sum(actual_quantity), sur les semaines terminées.
CREATE OR REPLACE VIEW bi.fact_forecast_accuracy AS
WITH actual AS (
    SELECT date_trunc('week', o.requested_delivery_date)::date AS week_start,
           o.customer_id,
           ol.article_id,
           sum(ol.quantity) AS quantity
      FROM ventes_customerorderline ol
      JOIN ventes_customerorder o ON o.id = ol.order_id
     WHERE o.status <> 'annulee'
     GROUP BY 1, 2, 3
), weeks AS (
    SELECT week_start FROM actual
    UNION
    SELECT week FROM previsions_forecastline
), s1 AS (
    SELECT w.week_start,
           (SELECT v.id
              FROM previsions_forecastversion v
             WHERE v.created_at < (w.week_start::timestamp AT TIME ZONE 'Europe/Paris')
               AND w.week_start BETWEEN v.first_week AND v.first_week + 49
             ORDER BY v.created_at DESC, v.id DESC
             LIMIT 1) AS version_id
      FROM weeks w
), forecast AS (
    SELECT s1.week_start, l.customer_id, l.article_id, l.quantity
      FROM s1
      JOIN previsions_forecastline l ON l.version_id = s1.version_id AND l.week = s1.week_start
), pairs AS (
    SELECT COALESCE(f.week_start, a.week_start) AS week_start,
           COALESCE(f.customer_id, a.customer_id) AS customer_id,
           COALESCE(f.article_id, a.article_id) AS article_id,
           COALESCE(f.quantity, 0) AS forecast_quantity,
           COALESCE(a.quantity, 0) AS actual_quantity
      FROM forecast f
      FULL JOIN actual a
        ON a.week_start = f.week_start AND a.customer_id = f.customer_id
       AND a.article_id = f.article_id
)
SELECT p.week_start,
       to_char(p.week_start, 'IYYY-"S"IW') AS week_label,
       p.week_start + 6 < bi.local_date(now()) AS is_complete,
       v.number AS version_number,
       p.customer_id,
       p.article_id,
       p.forecast_quantity,
       p.actual_quantity,
       abs(p.forecast_quantity - p.actual_quantity) AS abs_error
  FROM pairs p
  JOIN s1 ON s1.week_start = p.week_start
  JOIN previsions_forecastversion v ON v.id = s1.version_id;

-- --- TRS des lignes (phase 10) ----------------------------------------------------------

-- Arrêts de ligne saisis (hors arrêts annulés), avec leur durée
CREATE OR REPLACE VIEW bi.fact_line_stop AS
SELECT s.id AS stop_id,
       bi.local_date(s.started_at) AS date,
       s.line_id,
       l.code AS line_code,
       l.site_id,
       s.category,
       s.category IN ('maintenance_preventive', 'nettoyage_planifie') AS is_planned,
       extract(epoch FROM s.ended_at - s.started_at) / 3600 AS duration_hours,
       o.number AS production_order_number
  FROM production_linestop s
  JOIN referentiel_productionline l ON l.id = s.line_id
  LEFT JOIN production_productionorder o ON o.id = s.production_order_id
 WHERE s.cancelled_at IS NULL;

-- Temps d'une ligne par jour (même calcul que production.oee.line_times) :
-- TRS = sum(useful_hours) ÷ sum(required_hours) ; disponibilité = fonctionnement ÷ requis ;
-- performance = net ÷ fonctionnement ; qualité = utile ÷ net.
CREATE OR REPLACE VIEW bi.fact_line_time AS
WITH runs AS (
    SELECT o.line_id,
           bi.local_date(d.run_start) AS date,
           sum(extract(epoch FROM d.run_end - d.run_start) / 3600) AS opening_hours,
           sum(lot.initial_quantity + d.scrap_quantity) AS produced,
           sum(d.scrap_quantity) AS scrap
      FROM production_productiondeclaration d
      JOIN production_productionorder o ON o.id = d.order_id
      JOIN stocks_lot lot ON lot.id = d.lot_id
     WHERE d.run_start IS NOT NULL AND o.line_id IS NOT NULL
     GROUP BY 1, 2
), stops AS (
    SELECT line_id,
           date,
           sum(duration_hours) FILTER (WHERE is_planned) AS planned_stop_hours,
           sum(duration_hours) FILTER (WHERE NOT is_planned) AS unplanned_stop_hours
      FROM bi.fact_line_stop
     GROUP BY 1, 2
), days AS (
    SELECT COALESCE(r.line_id, s.line_id) AS line_id,
           COALESCE(r.date, s.date) AS date,
           COALESCE(r.opening_hours, 0) AS opening_hours,
           COALESCE(s.planned_stop_hours, 0) AS planned_stop_hours,
           COALESCE(s.unplanned_stop_hours, 0) AS unplanned_stop_hours,
           COALESCE(r.produced, 0) AS produced,
           COALESCE(r.scrap, 0) AS scrap
      FROM runs r
      FULL JOIN stops s ON s.line_id = r.line_id AND s.date = r.date
)
SELECT d.date,
       d.line_id,
       l.code AS line_code,
       l.site_id,
       l.capacity_per_hour,
       d.opening_hours,
       d.planned_stop_hours,
       d.unplanned_stop_hours,
       GREATEST(0, d.opening_hours - d.planned_stop_hours) AS required_hours,
       GREATEST(0, GREATEST(0, d.opening_hours - d.planned_stop_hours) - d.unplanned_stop_hours)
           AS operating_hours,
       d.produced,
       d.scrap,
       d.produced / l.capacity_per_hour AS net_hours,
       (d.produced - d.scrap) / l.capacity_per_hour AS useful_hours
  FROM days d
  JOIN referentiel_productionline l ON l.id = d.line_id;
