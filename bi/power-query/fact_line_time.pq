// Temps des lignes par jour (TRS) – vue bi.fact_line_time de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : fact_line_time (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "fact_line_time"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"date", type date},
        {"line_id", Int64.Type},
        {"line_code", type text},
        {"site_id", Int64.Type},
        {"capacity_per_hour", Int64.Type},
        {"opening_hours", type number},
        {"planned_stop_hours", type number},
        {"unplanned_stop_hours", type number},
        {"required_hours", type number},
        {"operating_hours", type number},
        {"produced", type number},
        {"scrap", type number},
        {"net_hours", type number},
        {"useful_hours", type number}
    })
in
    Types
