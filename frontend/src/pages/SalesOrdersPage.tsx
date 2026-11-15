import { ExternalLink, PackageCheck } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import type { CustomerOrder, CustomerOrderDetail, CustomerOrderLine } from '../api/sales'
import type { Customer, Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { SALES_ROLES, WAREHOUSE_ROLES, hasRole } from '../auth/roles'
import { type DataColumn, DataTable } from '../components/DataTable'
import { Drawer } from '../components/Drawer'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatDateTime, formatDecimal, formatMoney } from '../format'
import { useApi } from '../hooks/useApi'

const STATUSES = [
  { value: '', label: 'Tous les statuts' },
  { value: 'recue', label: 'Reçue' },
  { value: 'en_preparation', label: 'En préparation' },
  { value: 'expediee', label: 'Expédiée' },
  { value: 'annulee', label: 'Annulée' },
]

const LINE_COLUMNS: DataColumn<CustomerOrderLine>[] = [
  {
    id: 'article',
    header: 'Produit',
    sortValue: (line) => line.article_code,
    cell: (line) => (
      <>
        {line.article_code}
        <br />
        <small>{line.article_name}</small>
      </>
    ),
  },
  {
    id: 'quantity',
    header: 'Quantité',
    numeric: true,
    sortValue: (line) => Number(line.quantity),
    cell: (line) => `${formatDecimal(line.quantity)} u`,
  },
  {
    id: 'amount',
    header: 'Montant HT',
    numeric: true,
    sortValue: (line) => (line.amount === null ? null : Number(line.amount)),
    cell: (line) =>
      line.to_be_priced ? <span className="badge badge-warn">à valoriser</span> : formatMoney(line.amount),
  },
]

/** Contenu de la fiche d'une commande, chargé à l'ouverture du tiroir. */
function OrderSummary({ id }: { id: number }) {
  const order = useApi<CustomerOrderDetail>(`/api/ventes/orders/${id}/`)
  if (order.loading) return <p className="hint">Chargement…</p>
  if (order.error) return <p className="error">{order.error}</p>
  if (!order.data) return null
  const o = order.data
  return (
    <>
      <dl className="details drawer-details">
        <dt>Entrepôt livré</dt>
        <dd>
          {o.warehouse_code} – {o.warehouse_name}
        </dd>
        <dt>Livraison demandée</dt>
        <dd>{formatDate(o.requested_delivery_date)}</dd>
        <dt>Reçue le</dt>
        <dd>
          {formatDateTime(o.received_at)} ({o.source_label})
        </dd>
        {o.customer_reference && (
          <>
            <dt>Référence de l'enseigne</dt>
            <dd>{o.customer_reference}</dd>
          </>
        )}
        <dt>Montant HT</dt>
        <dd>{formatMoney(o.total_amount)}</dd>
        {o.shipments.length > 0 && (
          <>
            <dt>Bons de livraison</dt>
            <dd>
              {o.shipments.map((shipment, index) => (
                <span key={shipment.id}>
                  {index > 0 && ' · '}
                  <Link to={`/expeditions/${shipment.id}`}>{shipment.number}</Link>{' '}
                  <StatusBadge status={shipment.status} label={shipment.status_label} />
                </span>
              ))}
            </dd>
          </>
        )}
      </dl>
      <h3>Lignes ({o.lines.length})</h3>
      <DataTable caption="Lignes de la commande" rows={o.lines} rowKey={(line) => line.id} columns={LINE_COLUMNS} />
    </>
  )
}

export function SalesOrdersPage() {
  const { user } = useAuth()
  const customers = useApi<Paginated<Customer>>('/api/referentiel/customers/')
  const [status, setStatus] = useState('')
  const [customer, setCustomer] = useState('')
  const [search, setSearch] = useState('')
  const [opened, setOpened] = useState<CustomerOrder | null>(null)
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (customer) params.set('customer', customer)
  if (search) params.set('search', search)
  const { data, error } = useApi<Paginated<CustomerOrder>>(`/api/ventes/orders/?${params}`)

  const columns: DataColumn<CustomerOrder>[] = [
    {
      id: 'number',
      header: 'Numéro',
      sortValue: (order) => order.number,
      cell: (order) => (
        <>
          <button
            type="button"
            className="link-button lot-number"
            onClick={(event) => {
              event.stopPropagation()
              setOpened(order)
            }}
          >
            {order.number}
          </button>
          {order.customer_reference && (
            <>
              <br />
              <small>{order.customer_reference}</small>
            </>
          )}
        </>
      ),
    },
    {
      id: 'customer',
      header: 'Enseigne',
      sortValue: (order) => order.customer_code,
      cell: (order) => `${order.customer_code} – ${order.customer_name}`,
    },
    {
      id: 'warehouse',
      header: 'Entrepôt',
      sortValue: (order) => order.warehouse_name,
      cell: (order) => order.warehouse_name,
    },
    {
      id: 'received',
      header: 'Reçue le',
      sortValue: (order) => order.received_at,
      cell: (order) => formatDateTime(order.received_at),
    },
    {
      id: 'delivery',
      header: 'Livraison',
      sortValue: (order) => order.requested_delivery_date,
      cell: (order) => formatDate(order.requested_delivery_date),
    },
    {
      id: 'source',
      header: 'Origine',
      sortValue: (order) => order.source_label,
      cell: (order) => order.source_label,
    },
    {
      id: 'status',
      header: 'Statut',
      sortValue: (order) => order.status_label,
      cell: (order) => <StatusBadge status={order.status} label={order.status_label} />,
    },
    {
      id: 'amount',
      header: 'Montant HT',
      numeric: true,
      sortValue: (order) => (order.total_amount === null ? null : Number(order.total_amount)),
      cell: (order) => (
        <>
          {formatMoney(order.total_amount)}
          {order.to_be_priced && (
            <>
              {' '}
              <span className="badge badge-warn">à valoriser</span>
            </>
          )}
        </>
      ),
    },
  ]

  return (
    <section>
      <div className="page-title">
        <h1>Commandes clients</h1>
        <div className="actions">
          <Link to="/tarifs-vente">Tarifs de vente</Link>
          {hasRole(user, SALES_ROLES) && (
            <Link to="/ventes/nouvelle" className="button">
              + Saisir une commande
            </Link>
          )}
        </div>
      </div>
      <p className="page-intro">
        Clique sur une commande pour voir ses lignes et ses bons de livraison sans quitter la liste.
      </p>
      <div className="filters">
        <input
          type="search"
          placeholder="Numéro ou référence de l'enseigne"
          aria-label="Rechercher"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select aria-label="Enseigne" value={customer} onChange={(e) => setCustomer(e.target.value)}>
          <option value="">Toutes les enseignes</option>
          {customers.data?.results.map((c) => (
            <option key={c.id} value={c.id}>
              {c.code} – {c.name}
            </option>
          ))}
        </select>
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
          <p className="count">{data.count} commande(s)</p>
          <DataTable
            caption="Commandes clients"
            rows={data.results}
            columns={columns}
            rowKey={(order) => order.id}
            onRowClick={setOpened}
            empty="Aucune commande ne correspond."
          />
        </>
      )}
      {opened && (
        <Drawer
          open
          onClose={() => setOpened(null)}
          width={680}
          title={`Commande ${opened.number}`}
          subtitle={
            <>
              {opened.customer_code} – {opened.customer_name}{' '}
              <StatusBadge status={opened.status} label={opened.status_label} />
            </>
          }
          footer={
            <>
              <Link className="button secondary" to={`/ventes/${opened.id}`}>
                <ExternalLink size={15} aria-hidden="true" /> Fiche complète
              </Link>
              {opened.status === 'recue' && hasRole(user, WAREHOUSE_ROLES) && (
                <Link className="button" to={`/ventes/${opened.id}/preparation`}>
                  <PackageCheck size={15} aria-hidden="true" /> Préparer
                </Link>
              )}
            </>
          }
        >
          <OrderSummary id={opened.id} />
        </Drawer>
      )}
    </section>
  )
}
