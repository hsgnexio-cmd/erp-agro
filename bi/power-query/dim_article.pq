// Articles (MP, SF, PF, EM), familles, marques – vue bi.dim_article de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : dim_article (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "dim_article"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"article_id", Int64.Type},
        {"code", type text},
        {"name", type text},
        {"article_type", type text},
        {"article_type_label", type text},
        {"unit", type text},
        {"category_code", type text},
        {"family_code", type text},
        {"family_name", type text},
        {"factory_code", type text},
        {"brand", type text},
        {"format_size", Int64.Type},
        {"shelf_life_days", Int64.Type},
        {"active", type logical}
    })
in
    Types
