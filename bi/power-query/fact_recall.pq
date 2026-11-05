// Rappels lancés et durée du calcul – vue bi.fact_recall de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : fact_recall (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "fact_recall"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"recall_id", Int64.Type},
        {"recall_number", type text},
        {"date", type date},
        {"origin_lot_number", type text},
        {"origin_article_id", Int64.Type},
        {"duration_ms", Int64.Type},
        {"blocked_lots", Int64.Type},
        {"customers", Int64.Type}
    })
in
    Types
