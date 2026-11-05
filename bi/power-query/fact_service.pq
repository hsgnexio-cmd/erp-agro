// Taux de service, commande par commande – vue bi.fact_service de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : fact_service (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "fact_service"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"order_id", Int64.Type},
        {"order_number", type text},
        {"customer_id", Int64.Type},
        {"requested_delivery_date", type date},
        {"on_time_limit", type date},
        {"shipped_date", type date},
        {"is_counted", type logical},
        {"is_on_time", type logical},
        {"ordered", type number},
        {"delivered", type number},
        {"delivered_on_time", type number},
        {"delivered_late", type number},
        {"missing", type number}
    })
in
    Types
