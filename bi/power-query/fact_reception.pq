// Conformité des réceptions, ligne par ligne – vue bi.fact_reception de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : fact_reception (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "fact_reception"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"reception_line_id", Int64.Type},
        {"date", type date},
        {"reception_number", type text},
        {"supplier_id", Int64.Type},
        {"site_id", Int64.Type},
        {"article_id", Int64.Type},
        {"quantity", type number},
        {"is_compliant", type logical},
        {"non_compliance_reasons", type text}
    })
in
    Types
