// Enseignes (ENS1 à ENS6) – vue bi.dim_customer de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : dim_customer (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "dim_customer"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"customer_id", Int64.Type},
        {"code", type text},
        {"name", type text},
        {"customer_type", type text},
        {"sells_brand", type logical},
        {"sells_private_label", type logical},
        {"min_remaining_shelf_life_pct", type number},
        {"active", type logical}
    })
in
    Types
