// Mouvements de stock valorisés ; is_markdown = démarque – vue bi.fact_stock_movement de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : fact_stock_movement (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "fact_stock_movement"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"movement_id", Int64.Type},
        {"date", type date},
        {"created_at", type datetimezone},
        {"movement_type", type text},
        {"is_markdown", type logical},
        {"lot_id", Int64.Type},
        {"lot_number", type text},
        {"article_id", Int64.Type},
        {"site_id", Int64.Type},
        {"location_code", type text},
        {"quantity", type number},
        {"unit_value", type number},
        {"value", type number},
        {"reference", type text},
        {"reason", type text}
    })
in
    Types
