import { useState } from 'react'
import { Link } from 'react-router'
import type { ProductionOrder } from '../api/production'
import type { Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { PRODUCTION_ROLES, hasRole } from '../auth/roles'
import { type DataColumn, DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

const STATUSES = [
  { value: '', label: 'Tous les statuts' },
  { value: 'planifie', label: 'Planifié' },
  { value: 'lance', label: 'Lancé' },
  { value: 'termine', label: 'Terminé' },
  { value: 'annule', label: 'Annulé' },
]

/** Quantité produite par rapport à la quantité prévue. */
function Produced({ order }: { order: ProductionOrder }) {
  const planned = Number(order.planned_quantity)
  const rate = planned > 0 ? (Number(order.produced_quantity) / planned) * 100 : 0
  return (
    <span className="produced">
      <span>
        {formatDecimal(order.produced_quantity)} {order.unit}
      </span>
      <span className="load-track" aria-hidden="true">
        <span className="load-fill load-ok" style={{ width: `${Math.min(100, rate)}%` }} />
      </span>
    </span>
  )
}

const COLUMNS: DataColumn<ProductionOrder>[] = [
  {
    id: 'number',
    header: 'Numéro',
    sortValue: (order) => order.number,
    cell: (order) => <Link to={`/production/${order.id}`}>{order.number}</Link>,
  },
  {
    id: 'article',
    header: 'Article',
    sortValue: (order) => order.article_code,
    cell: (order) => (
      <>
        {order.article_code}
        <br />
        <small>{order.article_name}</small>
      </>
    ),
  },
  {
    id: 'date',
    header: 'Date',
    sortValue: (order) => order.planned_date,
    cell: (order) => formatDate(order.planned_date),
  },
  {
    id: 'line',
    header: 'Ligne',
    sortValue: (order) => order.line_code ?? `Cuisine ${order.site_code}`,
    cell: (order) => order.line_code ?? `Cuisine ${order.site_code}`,
  },
  {
    id: 'planned',
    header: 'Prévu',
    numeric: true,
    sortValue: (order) => Number(order.planned_quantity),
    cell: (order) => `${formatDecimal(order.planned_quantity)} ${order.unit}`,
  },
  {
    id: 'produced',
    header: 'Produit',
    numeric: true,
    sortValue: (order) => Number(order.produced_quantity),
    cell: (order) => <Produced order={order} />,
  },
  {
    id: 'status',
    header: 'Statut',
    sortValue: (order) => order.status_label,
    cell: (order) => <StatusBadge status={order.status} label={order.status_label} />,
  },
  {
    id: 'yield',
    header: 'Rendement',
    numeric: true,
    sortValue: (order) => (order.mass_yield === null ? null : Number(order.mass_yield)),
    cell: (order) =>
      order.mass_yield === null ? (
        '—'
      ) : (
        <span className={`badge badge-${Number(order.mass_yield) < 96 ? 'danger' : 'ok'}`}>
          {formatDecimal(order.mass_yield)} %
        </span>
      ),
  },
]

export function ProductionOrdersPage() {
  const { user } = useAuth()
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (search) params.set('search', search)
  const { data, error } = useApi<Paginated<ProductionOrder>>(`/api/production/orders/?${params}`)

  return (
    <section>
      <div className="page-title">
        <h1>Ordres de fabrication</h1>
        {hasRole(user, PRODUCTION_ROLES) && (
          <Link to="/production/nouveau" className="button">
            + Nouvel OF
          </Link>
        )}
      </div>
      <div className="filters">
        <input
          type="search"
          placeholder="Rechercher un numéro ou un article"
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
          caption="Ordres de fabrication"
          rows={data.results}
          columns={COLUMNS}
          rowKey={(order) => order.id}
          empty="Aucun ordre de fabrication ne correspond."
        />
      )}
    </section>
  )
}
