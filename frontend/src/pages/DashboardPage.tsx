import { useState } from 'react'
import type { Indicator, IndicatorStatus, Indicators } from '../api/pilotage'
import type { Customer, Paginated, Site } from '../api/types'
import { formatDate, todayIso } from '../format'
import { useApi } from '../hooks/useApi'

function daysAgoIso(days: number): string {
  const date = new Date(`${todayIso()}T12:00:00`)
  date.setDate(date.getDate() - days)
  return date.toISOString().slice(0, 10)
}

const UNIT_SUFFIX: Record<string, string> = { '%': ' %', '% du CA': ' %', jours: ' j', s: ' s' }

/** "98.5" + "%" → "98,5 %" */
function formatIndicator(value: string | null, unit: string): string {
  if (value === null) return '—'
  const number = Number(value).toLocaleString('fr-FR', { maximumFractionDigits: 2 })
  return `${number}${UNIT_SUFFIX[unit] ?? ` ${unit}`}`
}

/** Objectif atteint ? Même règle que le back-end (mini et / ou maxi). */
function statusOf(indicator: Indicator, value: string | null): IndicatorStatus {
  if (value === null) return 'sans_donnee'
  const number = Number(value)
  if (indicator.target_min !== null && number < Number(indicator.target_min)) return 'alerte'
  if (indicator.target_max !== null && number > Number(indicator.target_max)) return 'alerte'
  return 'ok'
}

const STATUS_LABELS: Record<IndicatorStatus, string> = {
  ok: 'Objectif atteint',
  alerte: 'Hors objectif',
  sans_donnee: 'Pas de donnée',
  indisponible: 'Non disponible',
}

const STATUS_BADGES: Record<IndicatorStatus, string> = {
  ok: 'badge-ok',
  alerte: 'badge-danger',
  sans_donnee: 'badge-neutral',
  indisponible: 'badge-neutral',
}

function Tile({ indicator }: { indicator: Indicator }) {
  return (
    <article className={`kpi kpi-${indicator.status}`} aria-label={indicator.label}>
      <header>
        <h2>{indicator.label}</h2>
        <span className={`badge ${STATUS_BADGES[indicator.status]}`}>
          {STATUS_LABELS[indicator.status]}
        </span>
      </header>
      <p className="kpi-value">
        {indicator.status === 'indisponible' ? '—' : formatIndicator(indicator.value, indicator.unit)}
      </p>
      <p className="kpi-target">Objectif : {indicator.target}</p>
      <p className="kpi-detail">{indicator.detail}</p>
      <p className="kpi-definition" title={indicator.definition}>
        {indicator.definition}
        {indicator.filters.length > 0 && <> · Filtres : {indicator.filters.join(', ')}</>}
      </p>
    </article>
  )
}

/** Tableau de bord de la direction : les indicateurs de la fiche entreprise. */
export function DashboardPage() {
  const [start, setStart] = useState(daysAgoIso(27))
  const [end, setEnd] = useState(todayIso())
  const [site, setSite] = useState('')
  const [customer, setCustomer] = useState('')
  const sites = useApi<Paginated<Site>>('/api/referentiel/sites/')
  const customers = useApi<Paginated<Customer>>('/api/referentiel/customers/')

  const params = new URLSearchParams({ start, end })
  if (site) params.set('site', site)
  if (customer) params.set('customer', customer)
  const { data, error, loading } = useApi<Indicators>(`/api/pilotage/indicators/?${params}`)

  const weekly = data?.indicators.filter((indicator) =>
    data.weeks.some((week) => indicator.code in week.values),
  )

  return (
    <section>
      <div className="page-title">
        <h1>Tableau de bord</h1>
        <div className="actions">
          <a className="button" href={`/api/pilotage/indicators/export/?${params}`}>
            ⬇ Exporter pour Excel (CSV)
          </a>
        </div>
      </div>
      <p className="hint">
        Les indicateurs de la fiche entreprise, calculés à partir des vues du schéma « bi » (les
        mêmes que celles de Power BI). Vert : objectif atteint ; rouge : hors objectif.
      </p>
      <div className="filters">
        <label className="stacked">
          Du
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label className="stacked">
          au
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <label className="stacked">
          Site
          <select value={site} onChange={(e) => setSite(e.target.value)}>
            <option value="">Tous les sites</option>
            {sites.data?.results.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} – {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className="stacked">
          Enseigne
          <select value={customer} onChange={(e) => setCustomer(e.target.value)}>
            <option value="">Toutes les enseignes</option>
            {customers.data?.results.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} – {item.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      {loading && <p className="count">Calcul des indicateurs…</p>}
      {data && (
        <>
          <p className="count">
            Période du {formatDate(data.start)} au {formatDate(data.end)}
          </p>
          <div className="kpi-grid">
            {data.indicators.map((indicator) => (
              <Tile key={indicator.code} indicator={indicator} />
            ))}
          </div>

          <h2>Évolution par semaine</h2>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Indicateur</th>
                  <th>Objectif</th>
                  {data.weeks.map((week) => (
                    <th
                      key={week.start}
                      className="num"
                      title={`Du ${formatDate(week.start)} au ${formatDate(week.end)}`}
                    >
                      {week.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {weekly?.map((indicator) => (
                  <tr key={indicator.code}>
                    <td>{indicator.label}</td>
                    <td>{indicator.target}</td>
                    {data.weeks.map((week) => {
                      const value = week.values[indicator.code] ?? null
                      const status = statusOf(indicator, value)
                      return (
                        <td key={week.start} className="num">
                          {value === null ? (
                            '—'
                          ) : (
                            <span
                              className={`badge ${STATUS_BADGES[status]}`}
                              title={STATUS_LABELS[status]}
                            >
                              {formatIndicator(value, indicator.unit)}
                            </span>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
