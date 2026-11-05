// Stock de fin de journée par article, site et statut, valorisé – vue bi.fact_stock_daily de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : fact_stock_daily (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "fact_stock_daily"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"date", type date},
        {"article_id", Int64.Type},
        {"site_id", Int64.Type},
        {"lot_status", type text},
        {"quantity", type number},
        {"value", type number}
    })
in
    Types
