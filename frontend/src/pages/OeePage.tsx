import { useState, type FormEvent } from 'react'
import { apiPost, errorMessages } from '../api/client'
import type { LineStop, Oee, ProductionLine } from '../api/production'
import type { Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { PRODUCTION_ROLES, hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { formatDateTime, formatDecimal, todayIso } from '../format'
import { useApi } from '../hooks/useApi'

const CATEGORIES = [
  ['panne', 'Panne'],
  ['changement_serie', 'Changement de série'],
  ['manque_matiere', 'Manque matière ou emballage'],
  ['manque_personnel', 'Manque de personnel'],
  ['reglage', 'Réglage, micro-arrêt'],
  ['maintenance_preventive', 'Maintenance préventive (planifiée)'],
  ['nettoyage_planifie', 'Nettoyage planifié'],
]

function daysAgoIso(days: number): string {
  const date = new Date(`${todayIso()}T12:00:00`)
  date.setDate(date.getDate() - days)
  return date.toISOString().slice(0, 10)
}

/** Badge vert si l'objectif est atteint, rouge sinon. */
function Rate({ value, target }: { value: string | null; target?: number }) {
  if (value === null) return <>—</>
  if (target === undefined) return <>{formatDecimal(value)} %</>
  return (
    <span className={`badge ${Number(value) >= target ? 'badge-ok' : 'badge-danger'}`}>
      {formatDecimal(value)} %
    </span>
  )
}

/** TRS des lignes : disponibilité × performance × qualité, Pareto et saisie des arrêts. */
export function OeePage() {
  const { user } = useAuth()
  const canEdit = hasRole(user, PRODUCTION_ROLES)
  const [start, setStart] = useState(daysAgoIso(27))
  const [end, setEnd] = useState(todayIso())
  const [site, setSite] = useState('')
  const [version, setVersion] = useState(0)
  const query = `start=${start}&end=${end}&site=${site}&v=${version}`
  const report = useApi<Oee>(`/api/production/oee/?${query}`)
  const stops = useApi<Paginated<LineStop>>(`/api/production/line-stops/?${query}`)
  const target = Number(report.data?.target ?? 70)
  const reload = () => setVersion((v) => v + 1)

  return (
    <section>
      <h1>TRS des lignes</h1>
      <p className="hint">
        TRS = temps utile (quantité bonne ÷ cadence) ÷ temps requis (plages de marche déclarées −
        arrêts planifiés) = disponibilité × performance × qualité. Objectif : ≥{' '}
        {formatDecimal(report.data?.target ?? '70')} %.
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
          Usine
          <select value={site} onChange={(e) => setSite(e.target.value)}>
            <option value="">Toutes les usines</option>
            <SiteOptions />
          </select>
        </label>
      </div>
      {report.error && <p className="error">{report.error}</p>}
      {report.data && (
        <>
          <div className="kpi-grid">
            {(
              [
                ['TRS', report.data.total.oee, target],
                ['Disponibilité', report.data.total.availability, undefined],
                ['Performance', report.data.total.performance, undefined],
                ['Qualité', report.data.total.quality, undefined],
              ] as const
            ).map(([label, value, goal]) => (
              <article key={label} className="kpi" aria-label={label}>
                <h2>{label}</h2>
                <p className="kpi-value">
                  <Rate value={value} target={goal} />
                </p>
              </article>
            ))}
          </div>

          <h2>Par ligne</h2>
          <div className="table-wrapper">
            <table aria-label="TRS par ligne">
              <thead>
                <tr>
                  <th>Ligne</th>
                  <th className="num">Ouverture</th>
                  <th className="num">Arrêts planifiés</th>
                  <th className="num">Arrêts non planifiés</th>
                  <th className="num">Produit (rebut)</th>
                  <th className="num">Disponibilité</th>
                  <th className="num">Performance</th>
                  <th className="num">Qualité</th>
                  <th className="num">TRS</th>
                </tr>
              </thead>
              <tbody>
                {report.data.lines.length === 0 && (
                  <tr>
                    <td colSpan={9}>Aucune plage de marche déclarée sur la période.</td>
                  </tr>
                )}
                {report.data.lines.map((row) => (
                  <tr key={row.line}>
                    <td title={row.line_name}>
                      {row.line_code} <small>{row.site_code}</small>
                    </td>
                    <td className="num">{formatDecimal(row.opening_hours)} h</td>
                    <td className="num">{formatDecimal(row.planned_stop_hours)} h</td>
                    <td className="num">{formatDecimal(row.unplanned_stop_hours)} h</td>
                    <td className="num">
                      {formatDecimal(row.produced)} <small>({formatDecimal(row.scrap)})</small>
                    </td>
                    <td className="num">
                      <Rate value={row.availability} />
                    </td>
                    <td className="num">
                      <Rate value={row.performance} />
                    </td>
                    <td className="num">
                      <Rate value={row.quality} />
                    </td>
                    <td className="num">
                      <Rate value={row.oee} target={target} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2>Causes d'arrêt (Pareto)</h2>
          <div className="table-wrapper">
            <table aria-label="Pareto des arrêts">
              <thead>
                <tr>
                  <th>Cause</th>
                  <th className="num">Arrêts</th>
                  <th className="num">Durée</th>
                  <th>Part des arrêts non planifiés</th>
                </tr>
              </thead>
              <tbody>
                {report.data.pareto.length === 0 && (
                  <tr>
                    <td colSpan={4}>Aucun arrêt sur la période.</td>
                  </tr>
                )}
                {report.data.pareto.map((row) => (
                  <tr key={row.category}>
                    <td>
                      {row.label} {row.planned && <small className="badge badge-neutral">planifié</small>}
                    </td>
                    <td className="num">{row.count}</td>
                    <td className="num">{formatDecimal(row.hours)} h</td>
                    <td>
                      {row.share !== null && (
                        <span className="pareto-bar">
                          <span style={{ width: `${row.share}%` }} />
                          {formatDecimal(row.share)} %
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <h2>Arrêts saisis</h2>
      {canEdit && <StopForm onDone={reload} />}
      {stops.data && <StopList stops={stops.data.results} canEdit={canEdit} onChange={reload} />}
    </section>
  )
}

function SiteOptions() {
  const sites = useApi<Paginated<{ id: number; code: string; name: string; site_type: string }>>(
    '/api/referentiel/sites/',
  )
  return (
    <>
      {sites.data?.results
        .filter((site) => site.site_type === 'usine')
        .map((site) => (
          <option key={site.id} value={site.id}>
            {site.code} – {site.name}
          </option>
        ))}
    </>
  )
}

function StopForm({ onDone }: { onDone: () => void }) {
  const lines = useApi<Paginated<ProductionLine>>('/api/referentiel/production-lines/')
  const [line, setLine] = useState('')
  const [startedAt, setStartedAt] = useState('')
  const [endedAt, setEndedAt] = useState('')
  const [category, setCategory] = useState('panne')
  const [comment, setComment] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setErrors([])
    try {
      await apiPost('/api/production/line-stops/', {
        line: Number(line),
        started_at: startedAt,
        ended_at: endedAt,
        category,
        comment,
      })
      setStartedAt('')
      setEndedAt('')
      setComment('')
      onDone()
    } catch (error) {
      setErrors(errorMessages(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="panel form" onSubmit={submit} aria-label="Saisir un arrêt">
      <ErrorList messages={errors} />
      <div className="form-grid">
        <label>
          Ligne
          <select value={line} onChange={(e) => setLine(e.target.value)} required>
            <option value="">Choisir…</option>
            {lines.data?.results.map((l) => (
              <option key={l.id} value={l.id}>
                {l.code} – {l.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Début
          <input type="datetime-local" value={startedAt} onChange={(e) => setStartedAt(e.target.value)} required />
        </label>
        <label>
          Fin
          <input type="datetime-local" value={endedAt} onChange={(e) => setEndedAt(e.target.value)} required />
        </label>
        <label>
          Cause
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {CATEGORIES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Commentaire
          <input value={comment} onChange={(e) => setComment(e.target.value)} />
        </label>
      </div>
      <div className="form-actions">
        <button type="submit" disabled={saving}>
          Enregistrer l'arrêt
        </button>
      </div>
    </form>
  )
}

function StopList(props: { stops: LineStop[]; canEdit: boolean; onChange: () => void }) {
  const { stops, canEdit, onChange } = props
  const [cancelling, setCancelling] = useState<number | null>(null)
  const [reason, setReason] = useState('')
  const [errors, setErrors] = useState<string[]>([])

  async function cancel(stop: LineStop) {
    setErrors([])
    try {
      await apiPost(`/api/production/line-stops/${stop.id}/cancel/`, { reason })
      setCancelling(null)
      setReason('')
      onChange()
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  return (
    <>
      <ErrorList messages={errors} />
      <div className="table-wrapper">
        <table aria-label="Arrêts saisis">
          <thead>
            <tr>
              <th>Ligne</th>
              <th>Début</th>
              <th className="num">Durée</th>
              <th>Cause</th>
              <th>OF</th>
              <th>Commentaire</th>
              <th>Saisi par</th>
              {canEdit && <th />}
            </tr>
          </thead>
          <tbody>
            {stops.length === 0 && (
              <tr>
                <td colSpan={canEdit ? 8 : 7}>Aucun arrêt sur la période.</td>
              </tr>
            )}
            {stops.map((stop) => (
              <tr key={stop.id} className={stop.cancelled_at ? 'inactive' : undefined}>
                <td>{stop.line_code}</td>
                <td>{formatDateTime(stop.started_at)}</td>
                <td className="num">{stop.minutes} min</td>
                <td>
                  {stop.category_label}
                  {stop.cancelled_at && (
                    <>
                      {' '}
                      <span className="badge badge-off">annulé</span> <small>{stop.cancel_reason}</small>
                    </>
                  )}
                </td>
                <td>{stop.production_order_number ?? ''}</td>
                <td>{stop.comment}</td>
                <td>{stop.created_by_name || 'automatique'}</td>
                {canEdit && (
                  <td>
                    {!stop.cancelled_at && cancelling !== stop.id && (
                      <button type="button" className="secondary" onClick={() => setCancelling(stop.id)}>
                        Annuler
                      </button>
                    )}
                    {cancelling === stop.id && (
                      <span className="inline-form">
                        <input
                          aria-label="Motif de l'annulation"
                          placeholder="Motif"
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                        />
                        <button type="button" className="danger" onClick={() => void cancel(stop)}>
                          Confirmer
                        </button>
                        <button type="button" className="secondary" onClick={() => setCancelling(null)}>
                          Retour
                        </button>
                      </span>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
