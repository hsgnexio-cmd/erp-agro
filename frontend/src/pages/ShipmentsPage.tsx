import { ExternalLink } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { Shipment, ShipmentDetail } from '../api/sales'
import type { Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { WAREHOUSE_ROLES, hasRole } from '../auth/roles'
import { type DataColumn, DataTable } from '../components/DataTable'
import { Drawer } from '../components/Drawer'
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

type SummaryRow = ShipmentDetail['summary'][number]
type ShipmentLine = ShipmentDetail['lines'][number]

const SUMMARY_COLUMNS: DataColumn<SummaryRow>[] = [
  {
    id: 'article',
    header: 'Produit',
    sortValue: (row) => row.article_code,
    cell: (row) => (
      <>
        {row.article_code}
        <br />
        <small>{row.article_name}</small>
      </>
    ),
  },
  {
    id: 'ordered',
    header: 'Commandé',
    numeric: true,
    sortValue: (row) => Number(row.ordered),
    cell: (row) => `${formatDecimal(row.ordered)} u`,
  },
  {
    id: 'prepared',
    header: 'Préparé',
    numeric: true,
    sortValue: (row) => Number(row.prepared),
    cell: (row) => `${formatDecimal(row.prepared)} u`,
  },
  {
    id: 'missing',
    header: 'Rupture',
    numeric: true,
    sortValue: (row) => Number(row.missing),
    cell: (row) =>
      Number(row.missing) > 0 ? <span className="badge badge-danger">{formatDecimal(row.missing)} u</span> : '—',
  },
]

const LINE_COLUMNS: DataColumn<ShipmentLine>[] = [
  { id: 'article', header: 'Produit', sortValue: (line) => line.article_code, cell: (line) => line.article_code },
  {
    id: 'lot',
    header: 'Lot',
    sortValue: (line) => line.lot_number,
    cell: (line) => <Link to={`/lots/${line.lot}`}>{line.lot_number}</Link>,
  },
  { id: 'expiry', header: 'DLC', sortValue: (line) => line.expiry_date, cell: (line) => formatDate(line.expiry_date) },
  {
    id: 'location',
    header: 'Emplacement',
    sortValue: (line) => line.location_code,
    cell: (line) => line.location_code,
  },
  {
    id: 'quantity',
    header: 'Quantité',
    numeric: true,
    sortValue: (line) => Number(line.quantity),
    cell: (line) => `${formatDecimal(line.quantity)} ${line.unit}`,
  },
  {
    id: 'fefo',
    header: 'Hors FEFO',
    sortValue: (line) => line.fefo_justification,
    cell: (line) => line.fefo_justification || '—',
  },
]

/** Contenu du tiroir d'un bon de livraison : chargement, quantités, lots. */
function ShipmentSummary({ id }: { id: number }) {
  const shipment = useApi<ShipmentDetail>(`/api/ventes/shipments/${id}/`)
  if (shipment.loading) return <p className="hint">Chargement…</p>
  if (shipment.error) return <p className="error">{shipment.error}</p>
  if (!shipment.data) return null
  const s = shipment.data
  return (
    <>
      {s.status === 'refusee' && (
        <p className="error-box">
          <strong>Expédition refusée :</strong> {s.refusal_reason}
        </p>
      )}
      <dl className="details drawer-details">
        <dt>Entrepôt livré</dt>
        <dd>
          {s.warehouse_code} – {s.warehouse_name}
        </dd>
        <dt>Livraison demandée</dt>
        <dd>{formatDate(s.requested_delivery_date)}</dd>
        <dt>Préparé</dt>
        <dd>
          {formatDateTime(s.prepared_at)}
          {s.prepared_by_name && ` par ${s.prepared_by_name}`}
        </dd>
        {s.status === 'expediee' && (
          <>
            <dt>Expédié</dt>
            <dd>
              {formatDateTime(s.shipped_at)} · {s.carrier} · {formatDecimal(s.loading_temperature)} °C
            </dd>
          </>
        )}
        <dt>Palettes</dt>
        <dd>{s.pallet_count}</dd>
      </dl>
      <h3>Commandé et préparé</h3>
      <DataTable caption="Commandé et préparé" rows={s.summary} rowKey={(row) => row.order_line} columns={SUMMARY_COLUMNS} />
      <h3>Lots préparés</h3>
      <DataTable caption="Lots préparés" rows={s.lines} rowKey={(line) => line.id} columns={LINE_COLUMNS} />
    </>
  )
}

export function ShipmentsPage() {
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [opened, setOpened] = useState<Shipment | null>(null)
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (search) params.set('search', search)
  const { data, error } = useApi<Paginated<Shipment>>(`/api/ventes/shipments/?${params}`)

  const columns: DataColumn<Shipment>[] = [
    {
      id: 'number',
      header: 'BL',
      sortValue: (s) => s.number,
      cell: (s) => (
        <Link to={`/expeditions/${s.id}`} onClick={(event) => event.stopPropagation()}>
          {s.number}
        </Link>
      ),
    },
    {
      id: 'order',
      header: 'Commande',
      sortValue: (s) => s.order_number,
      cell: (s) => (
        <Link to={`/ventes/${s.order}`} onClick={(event) => event.stopPropagation()}>
          {s.order_number}
        </Link>
      ),
    },
    {
      id: 'customer',
      header: 'Enseigne',
      sortValue: (s) => s.customer_code,
      cell: (s) => `${s.customer_code} – ${s.warehouse_name}`,
    },
    {
      id: 'delivery',
      header: 'Livraison',
      sortValue: (s) => s.requested_delivery_date,
      cell: (s) => formatDate(s.requested_delivery_date),
    },
    {
      id: 'status',
      header: 'Statut',
      sortValue: (s) => s.status_label,
      cell: (s) => <StatusBadge status={s.status} label={s.status_label} />,
    },
    {
      id: 'shipped',
      header: 'Expédié le',
      sortValue: (s) => (s.status === 'expediee' ? s.shipped_at : null),
      cell: (s) => (s.status === 'expediee' ? formatDateTime(s.shipped_at) : '—'),
    },
    {
      id: 'on_time',
      header: 'Délai',
      sortValue: (s) => (s.on_time === null ? null : s.on_time ? 1 : 0),
      cell: (s) => <OnTime value={s.on_time} />,
    },
    {
      id: 'quantity',
      header: 'Quantité',
      numeric: true,
      sortValue: (s) => Number(s.total_quantity),
      cell: (s) => `${formatDecimal(s.total_quantity)} u`,
    },
    {
      id: 'pallets',
      header: 'Palettes',
      numeric: true,
      sortValue: (s) => s.pallet_count,
      cell: (s) => s.pallet_count,
    },
  ]

  return (
    <section>
      <div className="page-title">
        <h1>Bons de livraison</h1>
        <div className="actions">
          <Link to="/taux-de-service">Taux de service</Link>
        </div>
      </div>
      <p className="page-intro">
        Un bon de livraison naît de la préparation d'une commande client (fiche de la commande,
        bouton « Préparer »). Clique sur une ligne pour voir les quantités et les lots préparés.
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
        <>
          <p className="count">{data.count} bon(s) de livraison</p>
          <DataTable
            caption="Bons de livraison"
            rows={data.results}
            columns={columns}
            rowKey={(s) => s.id}
            onRowClick={setOpened}
            empty="Aucun bon de livraison ne correspond."
          />
        </>
      )}
      {opened && (
        <Drawer
          open
          onClose={() => setOpened(null)}
          width={680}
          title={`Bon de livraison ${opened.number}`}
          subtitle={
            <>
              {opened.customer_code} – {opened.customer_name} · commande {opened.order_number}{' '}
              <StatusBadge status={opened.status} label={opened.status_label} />
            </>
          }
          footer={
            <Link className="button secondary" to={`/expeditions/${opened.id}`}>
              <ExternalLink size={15} aria-hidden="true" /> Fiche complète
              {opened.status === 'preparee' ? ' (expédier)' : opened.pallet_count > 0 ? ' (étiquettes)' : ''}
            </Link>
          }
        >
          <ShipmentSummary id={opened.id} />
        </Drawer>
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

      <div className="no-print">
        <h2>Commandé et préparé</h2>
        <DataTable caption="Commandé et préparé" rows={s.summary} rowKey={(row) => row.order_line} columns={SUMMARY_COLUMNS} />
        <h2>Lots préparés</h2>
        <DataTable caption="Lots préparés" rows={s.lines} rowKey={(line) => line.id} columns={LINE_COLUMNS} />
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
