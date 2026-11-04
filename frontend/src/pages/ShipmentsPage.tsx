import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { Shipment, ShipmentDetail } from '../api/sales'
import type { Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { WAREHOUSE_ROLES, hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatDateTime, formatDecimal, formatSscc } from '../format'
import { useApi } from '../hooks/useApi'

const STATUSES = [
  { value: '', label: 'Tous les statuts' },
  { value: 'preparee', label: 'Préparé (à expédier)' },
  { value: 'expediee', label: 'Expédié' },
  { value: 'refusee', label: 'Refusé (température)' },
  { value: 'annulee', label: 'Préparation annulée' },
]

function OnTime({ value }: { value: boolean | null }) {
  if (value === null) return <>—</>
  return value ? (
    <span className="badge badge-ok">à l'heure</span>
  ) : (
    <span className="badge badge-danger">en retard</span>
  )
}

export function ShipmentsPage() {
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (search) params.set('search', search)
  const { data, error } = useApi<Paginated<Shipment>>(`/api/ventes/shipments/?${params}`)

  return (
    <section>
      <div className="page-title">
        <h1>Bons de livraison</h1>
        <div className="actions">
          <Link to="/taux-de-service">Taux de service</Link>
        </div>
      </div>
      <p className="hint">
        Un bon de livraison naît de la préparation d'une commande client (fiche de la commande,
        bouton « Préparer »).
      </p>
      <div className="filters">
        <input
          type="search"
          placeholder="BL, commande ou SSCC"
          aria-label="Rechercher"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select aria-label="Statut" value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>BL</th>
                <th>Commande</th>
                <th>Enseigne</th>
                <th>Livraison</th>
                <th>Statut</th>
                <th>Expédié le</th>
                <th>Délai</th>
                <th className="num">Quantité</th>
                <th className="num">Palettes</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((s) => (
                <tr key={s.id}>
                  <td>
                    <Link to={`/expeditions/${s.id}`}>{s.number}</Link>
                  </td>
                  <td>
                    <Link to={`/ventes/${s.order}`}>{s.order_number}</Link>
                  </td>
                  <td>
                    {s.customer_code} – {s.warehouse_name}
                  </td>
                  <td>{formatDate(s.requested_delivery_date)}</td>
                  <td>
                    <StatusBadge status={s.status} label={s.status_label} />
                  </td>
                  <td>{s.status === 'expediee' ? formatDateTime(s.shipped_at) : '—'}</td>
                  <td>
                    <OnTime value={s.on_time} />
                  </td>
                  <td className="num">{formatDecimal(s.total_quantity)} u</td>
                  <td className="num">{s.pallet_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export function ShipmentDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const [version, setVersion] = useState(0)
  const shipment = useApi<ShipmentDetail>(`/api/ventes/shipments/${id}/?v=${version}`)
  const [carrier, setCarrier] = useState('')
  const [temperature, setTemperature] = useState('')
  const [reason, setReason] = useState('')
  const [errors, setErrors] = useState<string[]>([])

  if (shipment.error) return <p className="error">{shipment.error}</p>
  if (!shipment.data) return <p>Chargement…</p>
  const s = shipment.data
  const canAct = hasRole(user, WAREHOUSE_ROLES) && s.status === 'preparee'

  async function run(path: string, body: unknown) {
    setErrors([])
    try {
      await apiPost(`/api/ventes/shipments/${id}/${path}/`, body)
      setVersion((v) => v + 1)
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  function handleShip(event: FormEvent) {
    event.preventDefault()
    void run('ship', { carrier, temperature })
  }

  function handleCancel() {
    if (!window.confirm('Annuler cette préparation ? La commande pourra être préparée de nouveau.'))
      return
    void run('cancel', { reason })
  }

  return (
    <section>
      <p className="no-print">
        <Link to="/expeditions">← Retour aux bons de livraison</Link> ·{' '}
        <Link to={`/ventes/${s.order}`}>Commande {s.order_number}</Link>
      </p>
      <div className="page-title no-print">
        <h1>
          {s.number} <small>{s.customer_code} – {s.customer_name}</small>
        </h1>
        <StatusBadge status={s.status} label={s.status_label} />
      </div>
      {s.status === 'refusee' && (
        <p className="error-box no-print">
          <strong>Expédition refusée :</strong> {s.refusal_reason}. Les lots préparés ont été
          bloqués et une alerte a été créée ; la commande peut être préparée de nouveau avec
          d'autres lots.
        </p>
      )}
      {s.status === 'annulee' && (
        <p className="hint no-print">Préparation annulée : {s.refusal_reason}</p>
      )}

      <dl className="details no-print">
        <dt>Entrepôt livré</dt>
        <dd>
          {s.warehouse_code} – {s.warehouse_name}
        </dd>
        <dt>Livraison demandée</dt>
        <dd>
          {formatDate(s.requested_delivery_date)} (à expédier au plus tard la veille)
        </dd>
        <dt>Préparé</dt>
        <dd>
          {formatDateTime(s.prepared_at)}
          {s.prepared_by_name && ` par ${s.prepared_by_name}`}
        </dd>
        {s.shipped_at && s.status !== 'annulee' && (
          <>
            <dt>{s.status === 'expediee' ? 'Expédié' : 'Contrôlé au chargement'}</dt>
            <dd>
              {formatDateTime(s.shipped_at)}
              {s.shipped_by_name && ` par ${s.shipped_by_name}`} · {s.carrier} ·{' '}
              {formatDecimal(s.loading_temperature)} °C{' '}
              {s.status === 'expediee' && <OnTime value={s.on_time} />}
            </dd>
          </>
        )}
      </dl>

      <ErrorList messages={errors} />
      {canAct && (
        <form className="panel no-print" onSubmit={handleShip}>
          <h2>Expédier</h2>
          <p className="hint">
            Au-dessus de 4 °C dans le camion, l'expédition est refusée et les lots sont bloqués.
          </p>
          <div className="form-grid">
            <label className="stacked">
              Transporteur
              <input value={carrier} onChange={(e) => setCarrier(e.target.value)} required />
            </label>
            <label className="stacked">
              Température au chargement (°C)
              <input
                type="number"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(e.target.value)}
                required
              />
            </label>
          </div>
          <div className="form-actions">
            <button type="submit">Expédier</button>
          </div>
          <h3>Annuler la préparation</h3>
          <div className="actions">
            <input
              aria-label="Motif de l'annulation"
              placeholder="Motif (obligatoire)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <button type="button" className="secondary" onClick={handleCancel}>
              Annuler la préparation
            </button>
          </div>
        </form>
      )}

      <h2 className="no-print">Commandé et préparé</h2>
      <div className="table-wrapper no-print">
        <table>
          <thead>
            <tr>
              <th>Produit</th>
              <th className="num">Commandé</th>
              <th className="num">Préparé</th>
              <th className="num">Rupture</th>
            </tr>
          </thead>
          <tbody>
            {s.summary.map((row) => (
              <tr key={row.order_line}>
                <td>
                  {row.article_code} – {row.article_name}
                </td>
                <td className="num">{formatDecimal(row.ordered)} u</td>
                <td className="num">{formatDecimal(row.prepared)} u</td>
                <td className="num">
                  {Number(row.missing) > 0 ? (
                    <span className="badge badge-danger">{formatDecimal(row.missing)} u</span>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="no-print">Lots préparés</h2>
      <div className="table-wrapper no-print">
        <table>
          <thead>
            <tr>
              <th>Produit</th>
              <th>Lot</th>
              <th>DLC</th>
              <th>Emplacement</th>
              <th className="num">Quantité</th>
              <th>Hors FEFO</th>
            </tr>
          </thead>
          <tbody>
            {s.lines.map((line) => (
              <tr key={line.id}>
                <td>{line.article_code}</td>
                <td>
                  <Link to={`/lots/${line.lot}`}>{line.lot_number}</Link>
                </td>
                <td>{formatDate(line.expiry_date)}</td>
                <td>{line.location_code}</td>
                <td className="num">
                  {formatDecimal(line.quantity)} {line.unit}
                </td>
                <td>{line.fefo_justification || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {s.pallets.length > 0 && (
        <>
          <div className="page-title no-print">
            <h2>Palettes ({s.pallets.length})</h2>
            <button type="button" className="secondary" onClick={() => window.print()}>
              Imprimer les étiquettes
            </button>
          </div>
          <div className="pallet-labels">
            {s.pallets.map((pallet) => (
              <article key={pallet.id} className="pallet-label">
                <header>
                  <strong>Brévanne Traiteur</strong> – Plateforme PFN
                  <span>
                    Palette {pallet.rank} / {s.pallets.length}
                  </span>
                </header>
                <p>
                  <strong>Destinataire :</strong> {s.customer_name} – {s.warehouse_name}
                  <br />
                  <strong>BL :</strong> {s.number} · <strong>Commande :</strong> {s.order_number}
                  <br />
                  <strong>Livraison :</strong> {formatDate(s.requested_delivery_date)}
                </p>
                <table>
                  <thead>
                    <tr>
                      <th>Produit</th>
                      <th>Lot</th>
                      <th>DLC</th>
                      <th className="num">Qté</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pallet.lines.map((line) => (
                      <tr key={line.id}>
                        <td>{line.article_code}</td>
                        <td>{line.lot_number}</td>
                        <td>{formatDate(line.expiry_date)}</td>
                        <td className="num">{formatDecimal(line.quantity)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="sscc">
                  SSCC <strong>{formatSscc(pallet.sscc)}</strong>
                  <br />
                  <small>{formatDecimal(pallet.total_quantity)} unités</small>
                </p>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
