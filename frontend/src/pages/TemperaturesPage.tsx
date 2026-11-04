import { useState, type FormEvent } from 'react'
import { apiPost, errorMessages } from '../api/client'
import type {
  ColdRoomStatus,
  TemperatureReading,
  TemperatureReadingResult,
} from '../api/monitoring'
import type { Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { formatDateTime, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

const MONITORING_ROLES = ['admin', 'qualite', 'magasinier']

function limits(min: string | null, max: string | null): string {
  if (min !== null && max !== null) return `${formatDecimal(min)} à ${formatDecimal(max)} °C`
  if (max !== null) return `≤ ${formatDecimal(max)} °C`
  return '—'
}

/** Relevés de température des chambres froides (règle 7 : chaîne du froid). */
export function TemperaturesPage() {
  const { user } = useAuth()
  const [version, setVersion] = useState(0)
  const rooms = useApi<ColdRoomStatus[]>(`/api/stocks/temperatures/latest/?v=${version}`)
  const history = useApi<Paginated<TemperatureReading>>(`/api/stocks/temperatures/?v=${version}`)

  const [location, setLocation] = useState('')
  const [temperature, setTemperature] = useState('')
  const [comment, setComment] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [result, setResult] = useState<TemperatureReadingResult | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors([])
    setResult(null)
    try {
      const saved = await apiPost<TemperatureReadingResult>('/api/stocks/temperatures/', {
        location: Number(location),
        temperature,
        comment,
      })
      setResult(saved)
      setTemperature('')
      setComment('')
      setVersion((v) => v + 1)
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  return (
    <section>
      <h1>Températures</h1>

      {hasRole(user, MONITORING_ROLES) && (
        <form className="panel" onSubmit={handleSubmit}>
          <h2>Nouveau relevé</h2>
          <div className="form-grid">
            <label className="stacked">
              Chambre froide
              <select value={location} onChange={(e) => setLocation(e.target.value)} required>
                <option value="">— Choisir —</option>
                {rooms.data?.map((room) => (
                  <option key={room.location} value={room.location}>
                    {room.location_code} – {room.location_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked">
              Température (°C)
              <input
                type="number"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(e.target.value)}
                required
              />
            </label>
            <label className="stacked">
              Commentaire
              <input value={comment} onChange={(e) => setComment(e.target.value)} />
            </label>
          </div>
          <div className="form-actions">
            <button type="submit">Enregistrer le relevé</button>
          </div>
        </form>
      )}

      <ErrorList messages={errors} />
      {result &&
        (result.is_compliant ? (
          <p className="status status-ok" role="status">
            Relevé conforme : {formatDecimal(result.temperature)} °C en {result.location_code}.
          </p>
        ) : (
          <div className="error-box" role="alert">
            <strong>Écart de température !</strong> {result.alert}
            {result.blocked_lots.length > 0 && (
              <p>Lots bloqués automatiquement : {result.blocked_lots.join(', ')}</p>
            )}
          </div>
        ))}

      <h2>Dernier relevé par chambre froide</h2>
      {rooms.data && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Chambre froide</th>
                <th>Site</th>
                <th>Limites</th>
                <th className="num">Dernier relevé</th>
                <th>Le</th>
              </tr>
            </thead>
            <tbody>
              {rooms.data.map((room) => {
                const last = room.last_reading
                return (
                  <tr key={room.location}>
                    <td>
                      {room.location_code} – {room.location_name}
                    </td>
                    <td>{room.site_code}</td>
                    <td>{limits(room.min_allowed, room.max_allowed)}</td>
                    <td className="num">
                      {last ? (
                        <span className={`badge badge-${last.is_compliant ? 'ok' : 'danger'}`}>
                          {formatDecimal(last.temperature)} °C
                        </span>
                      ) : (
                        <span className="badge badge-warn">Aucun relevé</span>
                      )}
                    </td>
                    <td>{last ? formatDateTime(last.measured_at) : '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <h2>Historique des relevés</h2>
      {history.data && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Emplacement</th>
                <th className="num">Température</th>
                <th>Limites</th>
                <th>Par</th>
                <th>Commentaire</th>
              </tr>
            </thead>
            <tbody>
              {history.data.results.map((reading) => (
                <tr key={reading.id}>
                  <td>{formatDateTime(reading.measured_at)}</td>
                  <td>{reading.location_code}</td>
                  <td className="num">
                    <span className={`badge badge-${reading.is_compliant ? 'ok' : 'danger'}`}>
                      {formatDecimal(reading.temperature)} °C
                    </span>
                  </td>
                  <td>{limits(reading.min_allowed, reading.max_allowed)}</td>
                  <td>{reading.user_name ?? '—'}</td>
                  <td className="wrap">{reading.comment || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
