// Calendrier (jours, semaines ISO, mois) – vue bi.dim_date de l'ERP Brévanne Traiteur.
// Nom de la requête à garder : dim_date (les mesures DAX de bi/mesures-dax.md l'utilisent).
// Serveur et base : à adapter si le port PostgreSQL n'est pas 5432 (POSTGRES_HOST_PORT).
let
    Source = PostgreSQL.Database("localhost:5432", "erp_agro"),
    Vue = Source{[Schema = "bi", Item = "dim_date"]}[Data],
    Types = Table.TransformColumnTypes(Vue, {
        {"date", type date},
        {"iso_year", Int64.Type},
        {"iso_week", Int64.Type},
        {"week_start", type date},
        {"week_label", type text},
        {"year", Int64.Type},
        {"month", Int64.Type},
        {"day_of_week", Int64.Type}
    })
in
    Types
