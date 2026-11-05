// Rendement matière des OF terminés – vue bi.fact_production_yield de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : fact_production_yield (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "fact_production_yield"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"order_id", Int64.Type},
        {"order_number", type text},
        {"date", type date},
        {"site_id", Int64.Type},
        {"line_code", type text},
        {"article_id", Int64.Type},
        {"produced", type number},
        {"theoretical_mass", type number},
        {"actual_mass", type number},
        {"yield_pct", type number}
    })
in
    Types
