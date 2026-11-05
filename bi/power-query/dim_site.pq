// Sites (NAN, REN, PFN, MPE) – vue bi.dim_site de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : dim_site (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "dim_site"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"site_id", Int64.Type},
        {"code", type text},
        {"name", type text},
        {"site_type", type text},
        {"city", type text},
        {"active", type logical}
    })
in
    Types
