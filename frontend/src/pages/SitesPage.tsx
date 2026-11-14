import { Building2, Factory, Warehouse } from 'lucide-react'
import type { Location, Paginated, Site } from '../api/types'
import { type DataColumn, DataTable } from '../components/DataTable'
import { formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

function temperatureRange(location: Location): string {
  if (location.min_temperature === null || location.max_temperature === null) return '—'
  return `${formatDecimal(location.min_temperature)} à ${formatDecimal(location.max_temperature)} °C`
}

const ICONS: Record<string, typeof Factory> = { usine: Factory, entrepot: Warehouse }

const TONES: Record<string, string> = {
  froid_positif: 'info',
  froid_negatif: 'neutral',
  ambiant: 'warn',
}

const COLUMNS: DataColumn<Location>[] = [
  { id: 'code', header: 'Emplacement', sortValue: (l) => l.code, cell: (l) => l.code },
  { id: 'name', header: 'Nom', sortValue: (l) => l.name, cell: (l) => l.name },
  {
    id: 'class',
    header: 'Classe de température',
    sortValue: (l) => l.temperature_class_label,
    cell: (l) => (
      <span className={`badge badge-${TONES[l.temperature_class] ?? 'neutral'}`}>
        {l.temperature_class_label}
      </span>
    ),
  },
  { id: 'range', header: 'Plage', numeric: true, cell: temperatureRange },
]

export function SitesPage() {
  const sites = useApi<Paginated<Site>>('/api/referentiel/sites/')
  const locations = useApi<Paginated<Location>>('/api/referentiel/locations/')

  if (sites.error) return <p className="error">{sites.error}</p>

  return (
    <section>
      <h1>Sites et emplacements</h1>
      <p className="page-intro">
        Usines, plateforme et entrepôt, avec leurs emplacements et la température de chacun.
      </p>
      {sites.data?.results.map((site) => {
        const siteLocations =
          locations.data?.results.filter((location) => location.site === site.id) ?? []
        const Icon = ICONS[site.site_type] ?? Building2
        const cold = siteLocations.filter((l) => l.temperature_class !== 'ambiant').length
        return (
          <article key={site.id} className="site site-card">
            <header className="site-header">
              <span className="module-icon" aria-hidden="true">
                <Icon size={18} />
              </span>
              <h2>
                {site.code} – {site.name}{' '}
                <small>
                  {site.site_type_label} · {site.city}
                </small>
              </h2>
              <span className="card-count">
                {siteLocations.length} emplacement{siteLocations.length > 1 ? 's' : ''}
              </span>
              {cold > 0 && <span className="card-count">{cold} sous température dirigée</span>}
            </header>
            {siteLocations.length === 0 ? (
              <p>Aucun emplacement.</p>
            ) : (
              <DataTable
                caption={`Emplacements du site ${site.code}`}
                rows={siteLocations}
                columns={COLUMNS}
                rowKey={(location) => location.id}
              />
            )}
          </article>
        )
      })}
    </section>
  )
}
