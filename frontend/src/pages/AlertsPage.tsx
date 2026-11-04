import { useState } from 'react'
import { Link } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { Alert } from '../api/monitoring'
import type { Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { formatDateTime } from '../format'
import { useApi } from '../hooks/useApi'

const MONITORING_ROLES = ['admin', 'qualite', 'magasinier']

export function AlertsPage() {
  const { user } = useAuth()
  const [state, setState] = useState('open')
  const [version, setVersion] = useState(0)
  const alerts = useApi<Paginated<Alert>>(`/api/stocks/alerts/?state=${state}&v=${version}`)
  const [comments, setComments] = useState<Record<number, string>>({})
  const [errors, setErrors] = useState<string[]>([])

  async function resolve(alert: Alert) {
    setErrors([])
    try {
      await apiPost(`/api/stocks/alerts/${alert.id}/resolve/`, {
        comment: comments[alert.id] ?? '',
      })
      setVersion((v) => v + 1)
      // Met à jour le compteur du menu
      window.dispatchEvent(new Event('alerts-changed'))
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  const canResolve = hasRole(user, MONITORING_ROLES)

  return (
    <section>
      <h1>Alertes</h1>
      <div className="filters">
        <select aria-label="État" value={state} onChange={(e) => setState(e.target.value)}>
          <option value="open">À traiter</option>
          <option value="resolved">Traitées</option>
          <option value="">Toutes</option>
        </select>
      </div>
      <ErrorList messages={errors} />
      {alerts.data && alerts.data.results.length === 0 && <p>Aucune alerte.</p>}
      {alerts.data?.results.map((alert) => (
        <article key={alert.id} className={`alert-card level-${alert.level}`}>
          <header>
            <span className={`badge badge-${alert.level === 'critique' ? 'danger' : 'warn'}`}>
              {alert.level_label}
            </span>
            <strong>{alert.alert_type_label}</strong>
            <small>{formatDateTime(alert.created_at)}</small>
          </header>
          <p>{alert.message}</p>
          <p className="hint">
            {alert.lot && (
              <>
                Lot <Link to={`/lots/${alert.lot}`}>{alert.lot_number}</Link>{' '}
              </>
            )}
            {alert.location_code && <>· Emplacement {alert.location_code}</>}
          </p>
          {alert.is_open ? (
            canResolve && (
              <div className="resolve">
                <input
                  aria-label={`Commentaire alerte ${alert.id}`}
                  placeholder="Ce qui a été fait (obligatoire)"
                  value={comments[alert.id] ?? ''}
                  onChange={(e) => setComments({ ...comments, [alert.id]: e.target.value })}
                />
                <button type="button" onClick={() => void resolve(alert)}>
                  Marquer comme traitée
                </button>
              </div>
            )
          ) : (
            <p className="hint">
              ✔ Traitée le {formatDateTime(alert.resolved_at)}
              {alert.resolved_by_name && ` par ${alert.resolved_by_name}`} :{' '}
              {alert.resolution_comment}
            </p>
          )}
        </article>
      ))}
    </section>
  )
}
