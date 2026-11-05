// Lignes expédiées : quantités et chiffre d'affaires – vue bi.fact_sales de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : fact_sales (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "fact_sales"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"shipment_line_id", Int64.Type},
        {"date", type date},
        {"shipment_number", type text},
        {"order_number", type text},
        {"customer_id", Int64.Type},
        {"warehouse_code", type text},
        {"article_id", Int64.Type},
        {"lot_id", Int64.Type},
        {"quantity", type number},
        {"unit_price", type number},
        {"amount", type number}
    })
in
    Types
