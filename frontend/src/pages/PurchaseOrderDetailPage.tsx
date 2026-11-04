import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { Paginated, PurchaseOrder, Reception } from '../api/types'
import { useAuth } from '../auth/context'
import { PURCHASING_ROLES, WAREHOUSE_ROLES, hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { ReceptionResult } from '../components/ReceptionResult'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatDecimal, formatMoney } from '../format'
import { useApi } from '../hooks/useApi'

export function PurchaseOrderDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const fetched = useApi<PurchaseOrder>(`/api/achats/orders/${id}/`)
  const receptions = useApi<Paginated<Reception>>(`/api/achats/receptions/?order=${id}`)
  // Après « Envoyer » ou « Annuler », on affiche la commande renvoyée par le serveur
  const [updated, setUpdated] = useState<PurchaseOrder | null>(null)
  const [errors, setErrors] = useState<string[]>([])

  const order = updated?.id === Number(id) ? updated : fetched.data
  if (fetched.error) return <p className="error">{fetched.error}</p>
  if (!order) return <p>Chargement…</p>

  async function runAction(action: 'send' | 'cancel') {
    if (action === 'cancel' && !window.confirm('Annuler cette commande ?')) return
    setErrors([])
    try {
      setUpdated(await apiPost<PurchaseOrder>(`/api/achats/orders/${id}/${action}/`))
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  const canBuy = hasRole(user, PURCHASING_ROLES)
  const canReceive =
    hasRole(user, WAREHOUSE_ROLES) && ['envoyee', 'partiellement_recue'].includes(order.status)

  return (
    <section>
      <p>
        <Link to="/commandes">← Retour aux commandes</Link>
      </p>
      <div className="page-title">
        <h1>
          {order.number} <small>{order.supplier_name}</small>
        </h1>
        <StatusBadge status={order.status} label={order.status_label} />
      </div>

      <div className="actions">
        {canBuy && order.status === 'brouillon' && (
          <button type="button" onClick={() => void runAction('send')}>
            Envoyer au fournisseur
          </button>
        )}
        {canBuy && ['brouillon', 'envoyee'].includes(order.status) && (
          <button type="button" className="secondary" onClick={() => void runAction('cancel')}>
            Annuler la commande
          </button>
        )}
        {canReceive && (
          <Link to={`/commandes/${order.id}/reception`} className="button">
            Réceptionner
          </Link>
        )}
      </div>
      <ErrorList messages={errors} />

      <dl className="details">
        <dt>Fournisseur</dt>
        <dd>
          {order.supplier_code} – {order.supplier_name}
        </dd>
        <dt>Site de livraison</dt>
        <dd>{order.delivery_site_code}</dd>
        <dt>Commandée le</dt>
        <dd>{formatDate(order.order_date)}</dd>
        <dt>Livraison prévue</dt>
        <dd>{formatDate(order.expected_delivery_date)}</dd>
        <dt>Montant HT</dt>
        <dd>{formatMoney(order.total_amount)}</dd>
        {order.comment && (
          <>
            <dt>Commentaire</dt>
            <dd>{order.comment}</dd>
          </>
        )}
      </dl>

      <h2>Lignes</h2>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Article</th>
              <th>Désignation</th>
              <th className="num">Commandé</th>
              <th className="num">Reçu</th>
              <th className="num">Prix HT</th>
              <th className="num">Montant HT</th>
            </tr>
          </thead>
          <tbody>
            {order.lines.map((line) => (
              <tr key={line.id}>
                <td>{line.article_code}</td>
                <td>{line.article_name}</td>
                <td className="num">
                  {formatDecimal(line.quantity)} {line.unit}
                </td>
                <td className="num">
                  {formatDecimal(line.received_quantity)} {line.unit}
                </td>
                <td className="num">{formatDecimal(line.unit_price)} €</td>
                <td className="num">{formatMoney(line.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {receptions.data && receptions.data.results.length > 0 && (
        <>
          <h2>Réceptions</h2>
          {receptions.data.results.map((reception) => (
            <ReceptionResult key={reception.id} reception={reception} />
          ))}
        </>
      )}
    </section>
  )
}
