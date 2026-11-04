import { useState } from 'react'
import { Link } from 'react-router'
import type { ProductionOrder } from '../api/production'
import type { Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { PRODUCTION_ROLES, hasRole } from '../auth/roles'
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
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Numéro</th>
                <th>Article</th>
                <th>Date</th>
                <th>Ligne</th>
                <th className="num">Prévu</th>
                <th className="num">Produit</th>
                <th>Statut</th>
                <th className="num">Rendement</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((order) => (
                <tr key={order.id}>
                  <td>
                    <Link to={`/production/${order.id}`}>{order.number}</Link>
                  </td>
                  <td>
                    {order.article_code}
                    <br />
                    <small>{order.article_name}</small>
                  </td>
                  <td>{formatDate(order.planned_date)}</td>
                  <td>{order.line_code ?? `Cuisine ${order.site_code}`}</td>
                  <td className="num">
                    {formatDecimal(order.planned_quantity)} {order.unit}
                  </td>
                  <td className="num">
                    {formatDecimal(order.produced_quantity)} {order.unit}
                  </td>
                  <td>
                    <StatusBadge status={order.status} label={order.status_label} />
                  </td>
                  <td className="num">
                    {order.mass_yield === null ? (
                      '—'
                    ) : (
                      <span
                        className={`badge badge-${Number(order.mass_yield) < 96 ? 'danger' : 'ok'}`}
                      >
                        {formatDecimal(order.mass_yield)} %
                      </span>
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
