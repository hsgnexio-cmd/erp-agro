// Fiabilité des prévisions à S-1 – vue bi.fact_forecast_accuracy de l'ERP Brévanne Traiteur.
// Une ligne par semaine × enseigne × produit : prévision figée la semaine précédente et
// quantités réellement commandées.
// Nom de la requête à garder : fact_forecast_accuracy (utilisé par les mesures DAX).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "fact_forecast_accuracy"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"week_start", type date},
        {"week_label", type text},
        {"is_complete", type logical},
        {"version_number", type text},
        {"customer_id", Int64.Type},
        {"article_id", Int64.Type},
        {"forecast_quantity", type number},
        {"actual_quantity", type number},
        {"abs_error", type number}
    })
in
    Types
