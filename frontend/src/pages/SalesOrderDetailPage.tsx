import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { CustomerOrderDetail, CustomerOrderLine } from '../api/sales'
import { useAuth } from '../auth/context'
import { SALES_ROLES, WAREHOUSE_ROLES, hasRole } from '../auth/roles'
import { type DataColumn, DataTable } from '../components/DataTable'
import { ErrorList } from '../components/ErrorList'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatDateTime, formatDecimal, formatMoney } from '../format'
import { useApi } from '../hooks/useApi'

/** Colonnes des lignes ; « Livré » seulement une fois la commande expédiée. */
function lineColumns(shipped: boolean): DataColumn<CustomerOrderLine>[] {
  const columns: DataColumn<CustomerOrderLine>[] = [
    { id: 'article', header: 'Produit', sortValue: (line) => line.article_code, cell: (line) => line.article_code },
    { id: 'name', header: 'Désignation', sortValue: (line) => line.article_name, cell: (line) => line.article_name },
    {
      id: 'quantity',
      header: 'Quantité',
      numeric: true,
      sortValue: (line) => Number(line.quantity),
      cell: (line) => `${formatDecimal(line.quantity)} u`,
    },
  ]
  if (shipped) {
    columns.push({
      id: 'shipped',
      header: 'Livré',
      numeric: true,
      sortValue: (line) => Number(line.shipped_quantity),
      cell: (line) => (
        <>
          {formatDecimal(line.shipped_quantity)} u
          {Number(line.shipped_quantity) < Number(line.quantity) && (
            <>
              {' '}
              <span className="badge badge-danger">rupture</span>
            </>
          )}
        </>
      ),
    })
  }
  columns.push(
    {
      id: 'price',
      header: 'Prix HT',
      numeric: true,
      sortValue: (line) => (line.unit_price === null ? null : Number(line.unit_price)),
      cell: (line) =>
        line.to_be_priced ? <span className="badge badge-warn">à valoriser</span> : `${formatDecimal(line.unit_price)} €`,
    },
    {
      id: 'amount',
      header: 'Montant HT',
      numeric: true,
      sortValue: (line) => (line.amount === null ? null : Number(line.amount)),
      cell: (line) => (line.amount ? formatMoney(line.amount) : '—'),
    },
  )
  return columns
}

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

      <h2>Lignes ({o.lines.length})</h2>
      <DataTable caption="Lignes de la commande" rows={o.lines} rowKey={(line) => line.id} columns={lineColumns(o.status === 'expediee')} />
      {o.status === 'recue' && (
        <p className="hint">
          Préparation en deux temps : « Préparer » choisit les lots (FEFO, DLC minimale de
          l'enseigne), puis le bon de livraison permet d'expédier (transporteur, température).
        </p>
      )}
    </section>
  )
}
