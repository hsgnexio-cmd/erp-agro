import { useState } from 'react'
import { Link } from 'react-router'
import type { Paginated, PurchaseOrder } from '../api/types'
import { useAuth } from '../auth/context'
import { PURCHASING_ROLES, hasRole } from '../auth/roles'
import { type DataColumn, DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatMoney, todayIso } from '../format'
import { useApi } from '../hooks/useApi'

const STATUSES = [
  { value: '', label: 'Tous les statuts' },
  { value: 'brouillon', label: 'Brouillon' },
  { value: 'envoyee', label: 'Envoyée' },
  { value: 'partiellement_recue', label: 'Partiellement reçue' },
  { value: 'soldee', label: 'Soldée' },
  { value: 'annulee', label: 'Annulée' },
]

// Avancement d'une commande, de la création à la réception complète
const STEPS: Record<string, number> = { brouillon: 1, envoyee: 2, partiellement_recue: 3, soldee: 4 }

function Progress({ order }: { order: PurchaseOrder }) {
  const step = STEPS[order.status]
  if (!step) return <span className="hint">—</span>
  return (
    <span className="steps" role="img" aria-label={`Étape ${step} sur 4 : ${order.status_label}`}>
      {[1, 2, 3, 4].map((index) => (
        <span key={index} className={index <= step ? 'step done' : 'step'} />
      ))}
    </span>
  )
}

/** Respect du délai : une commande envoyée dont la date de livraison est passée est en retard. */
function Delay({ order }: { order: PurchaseOrder }) {
  if (order.status === 'soldee') return <span className="badge badge-ok">Reçue</span>
  if (order.status !== 'envoyee' && order.status !== 'partiellement_recue') {
    return <span className="hint">—</span>
  }
  const days = Math.round(
    (Date.parse(todayIso()) - Date.parse(order.expected_delivery_date)) / 86400000,
  )
  if (days > 0) return <span className="badge badge-danger">En retard de {days} j</span>
  if (days === 0) return <span className="badge badge-warn">Attendue aujourd'hui</span>
  return <span className="badge badge-neutral">Dans {-days} j</span>
}

const COLUMNS: DataColumn<PurchaseOrder>[] = [
  {
    id: 'number',
    header: 'Numéro',
    sortValue: (order) => order.number,
    cell: (order) => <Link to={`/commandes/${order.id}`}>{order.number}</Link>,
  },
  {
    id: 'supplier',
    header: 'Fournisseur',
    sortValue: (order) => order.supplier_name,
    cell: (order) => order.supplier_name,
  },
  {
    id: 'ordered',
    header: 'Commandée le',
    sortValue: (order) => order.order_date,
    cell: (order) => formatDate(order.order_date),
  },
  {
    id: 'expected',
    header: 'Livraison prévue',
    sortValue: (order) => order.expected_delivery_date,
    cell: (order) => formatDate(order.expected_delivery_date),
  },
  {
    id: 'status',
    header: 'Statut',
    sortValue: (order) => order.status_label,
    cell: (order) => <StatusBadge status={order.status} label={order.status_label} />,
  },
  { id: 'progress', header: 'Avancement', cell: (order) => <Progress order={order} /> },
  { id: 'delay', header: 'Délai', cell: (order) => <Delay order={order} /> },
  {
    id: 'amount',
    header: 'Montant HT',
    numeric: true,
    sortValue: (order) => (order.total_amount === null ? null : Number(order.total_amount)),
    cell: (order) => formatMoney(order.total_amount),
  },
]

export function PurchaseOrdersPage() {
  const { user } = useAuth()
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')

  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (search) params.set('search', search)
  const { data, error } = useApi<Paginated<PurchaseOrder>>(`/api/achats/orders/?${params}`)

  return (
    <section>
      <div className="page-title">
        <h1>Commandes fournisseurs</h1>
        {hasRole(user, PURCHASING_ROLES) && (
          <Link to="/commandes/nouvelle" className="button">
            + Nouvelle commande
          </Link>
        )}
      </div>
      <div className="filters">
        <input
          type="search"
          placeholder="Rechercher un numéro ou un fournisseur"
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
        <DataTable
          caption="Commandes fournisseurs"
          rows={data.results}
          columns={COLUMNS}
          rowKey={(order) => order.id}
          empty="Aucune commande ne correspond."
        />
      )}
    </section>
  )
}
