import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { CustomerOrderDetail } from '../api/sales'
import { useAuth } from '../auth/context'
import { SALES_ROLES, WAREHOUSE_ROLES, hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatDateTime, formatDecimal, formatMoney } from '../format'
import { useApi } from '../hooks/useApi'

export function SalesOrderDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const [version, setVersion] = useState(0)
  const order = useApi<CustomerOrderDetail>(`/api/ventes/orders/${id}/?v=${version}`)
  const [errors, setErrors] = useState<string[]>([])

  if (order.error) return <p className="error">{order.error}</p>
  if (!order.data) return <p>Chargement…</p>
  const o = order.data

  async function cancel() {
    if (!window.confirm('Annuler cette commande client ?')) return
    setErrors([])
    try {
      await apiPost(`/api/ventes/orders/${id}/cancel/`)
      setVersion((v) => v + 1)
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  return (
    <section>
      <p>
        <Link to="/ventes">← Retour aux commandes clients</Link>
      </p>
      <div className="page-title">
        <h1>
          {o.number} <small>{o.customer_code} – {o.customer_name}</small>
        </h1>
        <StatusBadge status={o.status} label={o.status_label} />
      </div>
      {o.status === 'recue' && (
        <div className="actions">
          {hasRole(user, WAREHOUSE_ROLES) && (
            <Link to={`/ventes/${o.id}/preparation`} className="button">
              Préparer
            </Link>
          )}
          {hasRole(user, SALES_ROLES) && (
            <button type="button" className="danger" onClick={() => void cancel()}>
              Annuler la commande
            </button>
          )}
        </div>
      )}
      {o.shipments.length > 0 && (
        <p>
          Bons de livraison :{' '}
          {o.shipments.map((shipment, index) => (
            <span key={shipment.id}>
              {index > 0 && ' · '}
              <Link to={`/expeditions/${shipment.id}`}>{shipment.number}</Link>{' '}
              <StatusBadge status={shipment.status} label={shipment.status_label} />
            </span>
          ))}
        </p>
      )}
      <ErrorList messages={errors} />

      <dl className="details">
        <dt>Entrepôt livré</dt>
        <dd>
          {o.warehouse_code} – {o.warehouse_name}
        </dd>
        <dt>Livraison demandée</dt>
        <dd>{formatDate(o.requested_delivery_date)}</dd>
        <dt>Reçue le</dt>
        <dd>
          {formatDateTime(o.received_at)} ({o.source_label}
          {o.edi_message_id && ` – message ${o.edi_message_id}`}
          {o.created_by_name && ` – saisie par ${o.created_by_name}`})
        </dd>
        {o.customer_reference && (
          <>
            <dt>Référence de l'enseigne</dt>
            <dd>{o.customer_reference}</dd>
          </>
        )}
        <dt>Montant HT</dt>
        <dd>{formatMoney(o.total_amount)}</dd>
        {o.comment && (
          <>
            <dt>Commentaire</dt>
            <dd>{o.comment}</dd>
          </>
        )}
      </dl>

      <h2>Lignes</h2>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Produit</th>
              <th>Désignation</th>
              <th className="num">Quantité</th>
              {o.status === 'expediee' && <th className="num">Livré</th>}
              <th className="num">Prix HT</th>
              <th className="num">Montant HT</th>
            </tr>
          </thead>
          <tbody>
            {o.lines.map((line) => (
              <tr key={line.id}>
                <td>{line.article_code}</td>
                <td>{line.article_name}</td>
                <td className="num">{formatDecimal(line.quantity)} u</td>
                {o.status === 'expediee' && (
                  <td className="num">
                    {formatDecimal(line.shipped_quantity)} u
                    {Number(line.shipped_quantity) < Number(line.quantity) && (
                      <>
                        {' '}
                        <span className="badge badge-danger">rupture</span>
                      </>
                    )}
                  </td>
                )}
                <td className="num">
                  {line.to_be_priced ? (
                    <span className="badge badge-warn">à valoriser</span>
                  ) : (
                    `${formatDecimal(line.unit_price)} €`
                  )}
                </td>
                <td className="num">{line.amount ? formatMoney(line.amount) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {o.status === 'recue' && (
        <p className="hint">
          Préparation en deux temps : « Préparer » choisit les lots (FEFO, DLC minimale de
          l'enseigne), puis le bon de livraison permet d'expédier (transporteur, température).
        </p>
      )}
    </section>
  )
}
