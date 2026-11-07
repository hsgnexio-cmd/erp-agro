// Lignes des versions de prévision figées – vue bi.fact_forecast de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : fact_forecast (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "fact_forecast"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"forecast_line_id", Int64.Type},
        {"version_number", type text},
        {"version_date", type date},
        {"version_source", type text},
        {"week_start", type date},
        {"week_label", type text},
        {"customer_id", Int64.Type},
        {"article_id", Int64.Type},
        {"base_quantity", type number},
        {"promo_coefficient", type number},
        {"is_adjusted", type logical},
        {"quantity", type number}
    })
in
    Types
