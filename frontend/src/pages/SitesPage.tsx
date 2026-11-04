import type { Location, Paginated, Site } from '../api/types'
import { formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

function temperatureRange(location: Location): string {
  if (location.min_temperature === null || location.max_temperature === null) return '—'
  return `${formatDecimal(location.min_temperature)} à ${formatDecimal(location.max_temperature)} °C`
}

export function SitesPage() {
  const sites = useApi<Paginated<Site>>('/api/referentiel/sites/')
  const locations = useApi<Paginated<Location>>('/api/referentiel/locations/')

  if (sites.error) return <p className="error">{sites.error}</p>

  return (
    <section>
      <h1>Sites et emplacements</h1>
      {sites.data?.results.map((site) => {
        const siteLocations =
          locations.data?.results.filter((location) => location.site === site.id) ?? []
        return (
          <article key={site.id} className="site">
            <h2>
              {site.code} – {site.name} <small>{site.site_type_label} · {site.city}</small>
            </h2>
            {siteLocations.length === 0 ? (
              <p>Aucun emplacement.</p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Emplacement</th>
                      <th>Nom</th>
                      <th>Classe de température</th>
                      <th>Plage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {siteLocations.map((location) => (
                      <tr key={location.id} className={location.active ? '' : 'inactive'}>
                        <td>{location.code}</td>
                        <td>{location.name}</td>
                        <td>{location.temperature_class_label}</td>
                        <td>{temperatureRange(location)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>
        )
      })}
    </section>
  )
}
