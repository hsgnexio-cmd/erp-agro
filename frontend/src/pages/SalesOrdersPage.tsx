import { useState } from 'react'
import { Link } from 'react-router'
import type { CustomerOrder } from '../api/sales'
import type { Customer, Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { SALES_ROLES, hasRole } from '../auth/roles'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatDateTime, formatMoney } from '../format'
import { useApi } from '../hooks/useApi'

const STATUSES = [
  { value: '', label: 'Tous les statuts' },
  { value: 'recue', label: 'Reçue' },
  { value: 'en_preparation', label: 'En préparation' },
  { value: 'expediee', label: 'Expédiée' },
  { value: 'annulee', label: 'Annulée' },
]

export function SalesOrdersPage() {
  const { user } = useAuth()
  const customers = useApi<Paginated<Customer>>('/api/referentiel/customers/')
  const [status, setStatus] = useState('')
  const [customer, setCustomer] = useState('')
  const [search, setSearch] = useState('')
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (customer) params.set('customer', customer)
  if (search) params.set('search', search)
  const { data, error } = useApi<Paginated<CustomerOrder>>(`/api/ventes/orders/?${params}`)

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
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Numéro</th>
                <th>Enseigne</th>
                <th>Entrepôt</th>
                <th>Reçue le</th>
                <th>Livraison</th>
                <th>Origine</th>
                <th>Statut</th>
                <th className="num">Montant HT</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((order) => (
                <tr key={order.id}>
                  <td>
                    <Link to={`/ventes/${order.id}`}>{order.number}</Link>
                    {order.customer_reference && (
                      <>
                        <br />
                        <small>{order.customer_reference}</small>
                      </>
                    )}
                  </td>
                  <td>
                    {order.customer_code} – {order.customer_name}
                  </td>
                  <td>{order.warehouse_name}</td>
                  <td>{formatDateTime(order.received_at)}</td>
                  <td>{formatDate(order.requested_delivery_date)}</td>
                  <td>{order.source_label}</td>
                  <td>
                    <StatusBadge status={order.status} label={order.status_label} />
                  </td>
                  <td className="num">
                    {formatMoney(order.total_amount)}
                    {order.to_be_priced && (
                      <>
                        {' '}
                        <span className="badge badge-warn">à valoriser</span>
                      </>
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
