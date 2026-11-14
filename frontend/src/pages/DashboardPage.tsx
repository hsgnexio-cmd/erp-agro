import { Download, Info } from 'lucide-react'
import { useState } from 'react'
import type { Indicator, IndicatorStatus, IndicatorWeek, Indicators } from '../api/pilotage'
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

const STATUS_COLORS: Record<IndicatorStatus, string> = {
  ok: '#166534',
  alerte: '#b91c1c',
  sans_donnee: '#6b7280',
  indisponible: '#6b7280',
}

/** Jauge horizontale : où se situe la valeur par rapport à l'objectif (mini et / ou maxi). */
function Gauge({ indicator }: { indicator: Indicator }) {
  if (indicator.value === null || indicator.status === 'indisponible') return null
  const value = Number(indicator.value)
  const min = indicator.target_min === null ? null : Number(indicator.target_min)
  const max = indicator.target_max === null ? null : Number(indicator.target_max)
  // Échelle : 0 à 100 pour un pourcentage à atteindre, sinon un peu au-delà du plus grand repère
  const top =
    indicator.unit === '%' && max === null ? 100 : Math.max(value, min ?? 0, max ?? 0) * 1.25 || 1
  const position = (n: number) => `${Math.min(100, Math.max(0, (n / top) * 100))}%`
  return (
    <div className="kpi-gauge" aria-hidden="true">
      {min !== null && max !== null && (
        <span className="kpi-gauge-zone" style={{ left: position(min), right: `calc(100% - ${position(max)})` }} />
      )}
      <span
        className="kpi-gauge-fill"
        style={{ width: position(value), background: STATUS_COLORS[indicator.status] }}
      />
      {min !== null && <span className="kpi-gauge-mark" style={{ left: position(min) }} />}
      {max !== null && <span className="kpi-gauge-mark" style={{ left: position(max) }} />}
    </div>
  )
}

/** Mini-courbe de l'évolution par semaine (les 6 dernières semaines de la période). */
function Sparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return null
  const width = 96
  const height = 30
  const low = Math.min(...values)
  const span = Math.max(...values) - low || 1
  const points = values.map((value, index) => {
    const x = (index / (values.length - 1)) * (width - 6) + 3
    const y = height - 4 - ((value - low) / span) * (height - 8)
    return [x, y] as const
  })
  const [lastX, lastY] = points[points.length - 1]
  return (
    <svg className="kpi-spark" width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <polyline
        points={points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={lastX} cy={lastY} r="3" fill={color} />
    </svg>
  )
}

function Tile({ indicator, weeks }: { indicator: Indicator; weeks: IndicatorWeek[] }) {
  const tooltipId = `formule-${indicator.code}`
  const trend = weeks
    .map((week) => week.values[indicator.code])
    .filter((value): value is string => value !== null && value !== undefined)
    .map(Number)
    .slice(-6)
  return (
    <article className={`kpi kpi-${indicator.status}`} aria-label={indicator.label}>
      <header>
        <h2>{indicator.label}</h2>
        <span className="kpi-info">
          <button type="button" className="kpi-info-button" aria-label="Formule de calcul" aria-describedby={tooltipId}>
            <Info size={15} aria-hidden="true" />
          </button>
          <span className="kpi-tooltip" role="tooltip" id={tooltipId}>
            {indicator.definition}
            {indicator.filters.length > 0 && <> · Filtres : {indicator.filters.join(', ')}</>}
          </span>
        </span>
        <span className={`badge ${STATUS_BADGES[indicator.status]}`}>
          {STATUS_LABELS[indicator.status]}
        </span>
      </header>
      <div className="kpi-main">
        <p className="kpi-value">
          {indicator.status === 'indisponible' ? '—' : formatIndicator(indicator.value, indicator.unit)}
        </p>
        <Sparkline values={trend} color={STATUS_COLORS[indicator.status]} />
      </div>
      <Gauge indicator={indicator} />
      <p className="kpi-target">Objectif : {indicator.target}</p>
      <p className="kpi-detail">{indicator.detail}</p>
    </article>
  )
}

/** Un indicateur tient-il compte de ce filtre (« site », « enseigne ») ? */
function usesFilter(indicators: Indicator[] | undefined, name: string): boolean {
  return (indicators ?? []).some((indicator) =>
    indicator.filters.some((filter) => filter.split(' ')[0] === name),
  )
}

/**
 * Tableau de bord : chaque rôle voit les indicateurs de son métier, la direction voit tout
 * (liste filtrée par le serveur, voir backend/comptes/access.py).
 */
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

  // Derniers indicateurs reçus : les filtres restent affichés pendant un nouveau calcul
  const [shown, setShown] = useState<Indicators>()
  if (data && data !== shown) setShown(data)
  const showSite = site !== '' || usesFilter(shown?.indicators, 'site')
  const showCustomer = customer !== '' || usesFilter(shown?.indicators, 'enseigne')

  const weekly = data?.indicators.filter((indicator) =>
    data.weeks.some((week) => indicator.code in week.values),
  )

  return (
    <section>
      <div className="page-title">
        <h1>Tableau de bord</h1>
        <div className="actions">
          <a className="button" href={`/api/pilotage/indicators/export/?${params}`}>
            <Download size={16} aria-hidden="true" /> Exporter pour Excel (CSV)
          </a>
        </div>
      </div>
      <p className="page-intro">
        Les indicateurs de ton métier, avec leur objectif et leur évolution par semaine. La formule
        de chacun est dans l'infobulle <Info size={14} aria-hidden="true" />.
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
        {showSite && (
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
        )}
        {showCustomer && (
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
        )}
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
              <Tile key={indicator.code} indicator={indicator} weeks={data.weeks} />
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
