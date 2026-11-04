import { useState } from 'react'
import { Link } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { EdiMessage } from '../api/sales'
import type { Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { SALES_ROLES, hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { StatusBadge } from '../components/StatusBadge'
import { formatDateTime } from '../format'
import { useApi } from '../hooks/useApi'

/** Journal des messages EDI reçus des enseignes (simulés). */
export function EdiPage() {
  const { user } = useAuth()
  const [status, setStatus] = useState('')
  const [version, setVersion] = useState(0)
  const messages = useApi<Paginated<EdiMessage>>(
    `/api/ventes/edi-messages/?status=${status}&v=${version}`,
  )
  const [errors, setErrors] = useState<string[]>([])
  const [info, setInfo] = useState('')

  async function simulate() {
    setErrors([])
    setInfo('')
    try {
      const received = await apiPost<EdiMessage[]>('/api/ventes/edi-messages/simulate/')
      const rejected = received.filter((m) => m.status === 'rejete').length
      setInfo(`${received.length} message(s) reçu(s), dont ${rejected} rejeté(s).`)
      setVersion((v) => v + 1)
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  return (
    <section>
      <div className="page-title">
        <h1>Messages EDI</h1>
        {hasRole(user, SALES_ROLES) && (
          <button type="button" onClick={() => void simulate()}>
            Simuler les commandes du jour
          </button>
        )}
      </div>
      <p className="hint">
        Chaque jour de semaine à 9 h 30, les enseignes « envoient » leurs commandes. Un message
        correct devient une commande client ; sinon il est rejeté avec le motif.
      </p>
      {info && (
        <p className="status status-ok" role="status">
          {info}
        </p>
      )}
      <ErrorList messages={errors} />
      <div className="filters">
        <select aria-label="Statut" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Tous les messages</option>
          <option value="integre">Intégrés</option>
          <option value="rejete">Rejetés</option>
        </select>
      </div>
      {messages.data && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Message</th>
                <th>Enseigne</th>
                <th>Reçu le</th>
                <th>Statut</th>
                <th>Résultat</th>
              </tr>
            </thead>
            <tbody>
              {messages.data.results.map((m) => (
                <tr key={m.id}>
                  <td>
                    {m.message_id}
                    <details>
                      <summary>Contenu</summary>
                      <pre className="payload">{JSON.stringify(m.payload, null, 2)}</pre>
                    </details>
                  </td>
                  <td>{m.customer_code ?? '—'}</td>
                  <td>{formatDateTime(m.received_at)}</td>
                  <td>
                    <StatusBadge status={m.status} label={m.status_label} />
                  </td>
                  <td className="wrap">
                    {m.order ? (
                      <Link to={`/ventes/${m.order.id}`}>Commande {m.order.number}</Link>
                    ) : (
                      <ul className="errors">
                        {m.errors.map((error) => (
                          <li key={error}>{error}</li>
                        ))}
                      </ul>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
