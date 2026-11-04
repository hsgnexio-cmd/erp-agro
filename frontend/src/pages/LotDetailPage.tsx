import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { Location, LotDetail, Paginated, StockMovement } from '../api/types'
import { useAuth } from '../auth/context'
import { QUALITY_ROLES, WAREHOUSE_ROLES, hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatDateTime, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

type StatusAction = 'release' | 'block' | 'destroy'

export function LotDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  // Augmenté après chaque action, pour recharger la fiche et les mouvements
  const [version, setVersion] = useState(0)
  const lot = useApi<LotDetail>(`/api/stocks/lots/${id}/?v=${version}`)
  const movements = useApi<Paginated<StockMovement>>(`/api/stocks/movements/?lot=${id}&v=${version}`)
  const locations = useApi<Paginated<Location>>('/api/referentiel/locations/?active=true')

  const [reason, setReason] = useState('')
  const [fromLocation, setFromLocation] = useState('')
  const [toLocation, setToLocation] = useState('')
  const [quantity, setQuantity] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [message, setMessage] = useState('')

  if (lot.error) return <p className="error">{lot.error}</p>
  if (!lot.data) return <p>Chargement…</p>
  const l = lot.data

  async function run(path: string, body: unknown, success: string) {
    setErrors([])
    setMessage('')
    try {
      await apiPost(`/api/stocks/lots/${id}/${path}/`, body)
      setMessage(success)
      setReason('')
      setQuantity('')
      setVersion((v) => v + 1)
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  const statusAction = (action: StatusAction, success: string) => {
    if (action === 'destroy' && !window.confirm('Détruire ce lot ? Tout son stock sera sorti.')) {
      return
    }
    void run(action, { reason }, success)
  }

  function handleTransfer(event: FormEvent) {
    event.preventDefault()
    const from = fromLocation || String(l.stock_by_location[0]?.location ?? '')
    void run(
      'transfer',
      { from_location: Number(from), to_location: Number(toLocation), quantity, reason },
      'Transfert enregistré.',
    )
  }

  const isQuality = hasRole(user, QUALITY_ROLES)
  const isWarehouse = hasRole(user, WAREHOUSE_ROLES)
  // Chaîne du froid : seuls les emplacements à la bonne température sont proposés
  const destinations =
    locations.data?.results.filter(
      (location) => location.temperature_class === l.article_temperature_class,
    ) ?? []

  return (
    <section>
      <p>
        <Link to="/lots">← Retour aux lots</Link> ·{' '}
        <Link to={`/tracabilite?lot=${l.number}`}>Voir la traçabilité de ce lot</Link>
      </p>
      <div className="page-title">
        <h1>
          {l.number} <small>{l.article_code} – {l.article_name}</small>
        </h1>
        <StatusBadge status={l.status} label={l.status_label} />
      </div>
      {l.is_expired && l.status !== 'detruit' && (
        <p className="error-box">
          Lot périmé ({l.date_type} du {formatDate(l.expiry_date)}) : il ne peut plus être libéré.
        </p>
      )}
      {l.block_reason && (
        <p className="error-box">
          <strong>Motif de blocage :</strong> {l.block_reason}
        </p>
      )}

      <dl className="details">
        <dt>Article</dt>
        <dd>
          <Link to={`/articles/${l.article}`}>{l.article_code}</Link> – {l.article_name}
        </dd>
        <dt>Fournisseur</dt>
        <dd>
          {l.supplier_code ?? '—'} · lot {l.supplier_lot_number || '—'}
        </dd>
        {l.production_date && (
          <>
            <dt>Fabrication</dt>
            <dd>{formatDate(l.production_date)}</dd>
          </>
        )}
        <dt>Réception</dt>
        <dd>
          {formatDate(l.reception_date)}
          {l.reception_number && ` (${l.reception_number})`}
        </dd>
        <dt>{l.date_type === 'aucune' ? 'Date limite' : l.date_type}</dt>
        <dd>{formatDate(l.expiry_date)}</dd>
        <dt>Quantité</dt>
        <dd>
          {formatDecimal(l.quantity)} {l.unit} (reçu : {formatDecimal(l.initial_quantity)} {l.unit})
        </dd>
      </dl>

      <h2>Stock par emplacement</h2>
      {l.stock_by_location.length === 0 ? (
        <p>Plus de stock pour ce lot.</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Site</th>
                <th>Emplacement</th>
                <th className="num">Quantité</th>
              </tr>
            </thead>
            <tbody>
              {l.stock_by_location.map((row) => (
                <tr key={row.location}>
                  <td>{row.site_code}</td>
                  <td>
                    {row.location_code} – {row.location_name}
                  </td>
                  <td className="num">
                    {formatDecimal(row.quantity)} {l.unit}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {message && (
        <p className="status status-ok" role="status">
          {message}
        </p>
      )}
      <ErrorList messages={errors} />

      {isQuality && l.status !== 'detruit' && (
        <div className="panel">
          <h2>Décision qualité</h2>
          <label className="stacked">
            Motif {l.status === 'quarantaine' ? '(obligatoire pour bloquer)' : '(obligatoire)'}
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} />
          </label>
          <div className="actions">
            {l.status === 'quarantaine' && (
              <button type="button" onClick={() => statusAction('release', 'Lot libéré.')}>
                Libérer
              </button>
            )}
            {l.status === 'bloque' && (
              <button type="button" onClick={() => statusAction('release', 'Lot débloqué.')}>
                Débloquer
              </button>
            )}
            {['quarantaine', 'libere'].includes(l.status) && (
              <button
                type="button"
                className="secondary"
                onClick={() => statusAction('block', 'Lot bloqué.')}
              >
                Bloquer
              </button>
            )}
            {l.status === 'bloque' && (
              <button
                type="button"
                className="danger"
                onClick={() => statusAction('destroy', 'Lot détruit.')}
              >
                Détruire
              </button>
            )}
          </div>
        </div>
      )}

      {isWarehouse && l.status !== 'detruit' && l.stock_by_location.length > 0 && (
        <form className="panel" onSubmit={handleTransfer}>
          <h2>Transférer</h2>
          <div className="form-grid">
            <label className="stacked">
              Depuis
              <select value={fromLocation} onChange={(e) => setFromLocation(e.target.value)}>
                {l.stock_by_location.map((row) => (
                  <option key={row.location} value={row.location}>
                    {row.location_code} ({formatDecimal(row.quantity)} {l.unit})
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked">
              Vers
              <select value={toLocation} onChange={(e) => setToLocation(e.target.value)} required>
                <option value="">— Choisir —</option>
                {destinations.map((location) => (
                  <option key={location.id} value={location.id}>
                    {location.code} – {location.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked">
              Quantité ({l.unit})
              <input
                type="number"
                min="0"
                step="any"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                required
              />
            </label>
            <label className="stacked">
              Motif (facultatif)
              <input value={reason} onChange={(e) => setReason(e.target.value)} />
            </label>
          </div>
          <div className="form-actions">
            <button type="submit">Transférer</button>
          </div>
        </form>
      )}

      <h2>Historique des statuts</h2>
      {l.status_changes.length === 0 ? (
        <p>Aucun changement depuis la réception.</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Changement</th>
                <th>Motif</th>
                <th>Par</th>
              </tr>
            </thead>
            <tbody>
              {l.status_changes.map((change) => (
                <tr key={change.id}>
                  <td>{formatDateTime(change.changed_at)}</td>
                  <td>
                    {change.from_status_label} → {change.to_status_label}
                  </td>
                  <td className="wrap">{change.reason || '—'}</td>
                  <td>{change.user_name ?? 'ERP (automatique)'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2>Mouvements de stock</h2>
      {movements.data && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Emplacement</th>
                <th className="num">Quantité</th>
                <th>Motif</th>
                <th>Document</th>
                <th>Par</th>
              </tr>
            </thead>
            <tbody>
              {movements.data.results.map((m) => (
                <tr key={m.id}>
                  <td>{formatDateTime(m.created_at)}</td>
                  <td>{m.movement_type_label}</td>
                  <td>{m.location_code}</td>
                  <td className={`num ${Number(m.quantity) < 0 ? 'negative' : ''}`}>
                    {Number(m.quantity) > 0 ? '+' : ''}
                    {formatDecimal(m.quantity)} {m.unit}
                  </td>
                  <td className="wrap">{m.reason}</td>
                  <td>
                    {m.reference || '—'}
                    {m.produced_lot_number && (
                      <small>
                        {' '}
                        → <Link to={`/lots/${m.produced_lot}`}>{m.produced_lot_number}</Link>
                      </small>
                    )}
                    {m.customer_code && <small> → {m.customer_code}</small>}
                  </td>
                  <td>{m.user_name ?? 'ERP'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
