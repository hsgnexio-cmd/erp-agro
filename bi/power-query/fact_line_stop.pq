// Arrêts de ligne (Pareto) – vue bi.fact_line_stop de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : fact_line_stop (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "fact_line_stop"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"stop_id", Int64.Type},
        {"date", type date},
        {"line_id", Int64.Type},
        {"line_code", type text},
        {"site_id", Int64.Type},
        {"category", type text},
        {"is_planned", type logical},
        {"duration_hours", type number},
        {"production_order_number", type text}
    })
in
    Types
