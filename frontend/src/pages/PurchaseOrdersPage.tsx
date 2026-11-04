import { useState } from 'react'
import { Link } from 'react-router'
import type { Paginated, PurchaseOrder } from '../api/types'
import { useAuth } from '../auth/context'
import { PURCHASING_ROLES, hasRole } from '../auth/roles'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatMoney } from '../format'
import { useApi } from '../hooks/useApi'

const STATUSES = [
  { value: '', label: 'Tous les statuts' },
  { value: 'brouillon', label: 'Brouillon' },
  { value: 'envoyee', label: 'Envoyée' },
  { value: 'partiellement_recue', label: 'Partiellement reçue' },
  { value: 'soldee', label: 'Soldée' },
  { value: 'annulee', label: 'Annulée' },
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
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Numéro</th>
                <th>Fournisseur</th>
                <th>Commandée le</th>
                <th>Livraison prévue</th>
                <th>Statut</th>
                <th className="num">Montant HT</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((order) => (
                <tr key={order.id}>
                  <td>
                    <Link to={`/commandes/${order.id}`}>{order.number}</Link>
                  </td>
                  <td>{order.supplier_name}</td>
                  <td>{formatDate(order.order_date)}</td>
                  <td>{formatDate(order.expected_delivery_date)}</td>
                  <td>
                    <StatusBadge status={order.status} label={order.status_label} />
                  </td>
                  <td className="num">{formatMoney(order.total_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
