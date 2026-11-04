import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { CustomerOrderDetail, OrderableArticles } from '../api/sales'
import type { Customer, Paginated } from '../api/types'
import { ErrorList } from '../components/ErrorList'
import { formatDate, formatDecimal, formatMoney } from '../format'
import { useApi } from '../hooks/useApi'

interface Warehouse {
  id: number
  code: string
  name: string
  city: string
}

/** Saisie manuelle d'une commande client (reçue par téléphone, par exemple). */
export function SalesOrderFormPage() {
  const navigate = useNavigate()
  const customers = useApi<Paginated<Customer>>('/api/referentiel/customers/?active=true')
  const [customerId, setCustomerId] = useState('')
  const warehouses = useApi<Paginated<Warehouse>>(
    customerId ? `/api/referentiel/customer-warehouses/?customer=${customerId}&active=true` : null,
  )
  const catalog = useApi<OrderableArticles>(
    customerId ? `/api/ventes/orderable-articles/?customer=${customerId}` : null,
  )
  const [warehouseId, setWarehouseId] = useState('')
  const [deliveryDate, setDeliveryDate] = useState('')
  const [reference, setReference] = useState('')
  const [comment, setComment] = useState('')
  const [quantities, setQuantities] = useState<Record<number, string>>({})
  const [errors, setErrors] = useState<string[]>([])

  const earliest = catalog.data?.earliest_delivery_date ?? ''
  const delivery = deliveryDate || earliest
  const lines = (catalog.data?.articles ?? []).filter((a) => Number(quantities[a.article]) > 0)
  const total = lines.reduce(
    (sum, a) => sum + Number(quantities[a.article]) * Number(a.unit_price ?? 0),
    0,
  )

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors([])
    try {
      const order = await apiPost<CustomerOrderDetail>('/api/ventes/orders/', {
        customer: Number(customerId),
        warehouse: Number(warehouseId),
        requested_delivery_date: delivery,
        customer_reference: reference,
        comment,
        lines: lines.map((a) => ({ article: a.article, quantity: quantities[a.article] })),
      })
      navigate(`/ventes/${order.id}`)
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  return (
    <section>
      <p>
        <Link to="/ventes">← Retour aux commandes clients</Link>
      </p>
      <h1>Saisir une commande client</h1>
      <form className="form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label>
            Enseigne
            <select
              value={customerId}
              onChange={(e) => {
                setCustomerId(e.target.value)
                setWarehouseId('')
                setQuantities({})
                setDeliveryDate('')
              }}
              required
            >
              <option value="">— Choisir —</option>
              {customers.data?.results.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} – {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Entrepôt livré
            <select value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)} required>
              <option value="">— Choisir —</option>
              {warehouses.data?.results.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.code} – {w.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Livraison demandée
            <input
              type="date"
              min={earliest}
              value={delivery}
              onChange={(e) => setDeliveryDate(e.target.value)}
              required
            />
          </label>
          <label>
            Référence de l'enseigne
            <input value={reference} onChange={(e) => setReference(e.target.value)} />
          </label>
          <label>
            Commentaire
            <input value={comment} onChange={(e) => setComment(e.target.value)} />
          </label>
        </div>
        {earliest && (
          <p className="hint">
            Heure limite 11 h : livraison possible au plus tôt le {formatDate(earliest)}.
          </p>
        )}

        {catalog.data && (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Produit</th>
                  <th>Désignation</th>
                  <th className="num">Prix HT</th>
                  <th className="num">Quantité (u)</th>
                </tr>
              </thead>
              <tbody>
                {catalog.data.articles.map((a) => (
                  <tr key={a.article}>
                    <td>{a.article_code}</td>
                    <td>{a.article_name}</td>
                    <td className="num">
                      {a.unit_price ? (
                        `${formatDecimal(a.unit_price)} €`
                      ) : (
                        <span className="badge badge-warn">pas de tarif</span>
                      )}
                    </td>
                    <td className="num">
                      <input
                        type="number"
                        min="0"
                        step="12"
                        className="qty"
                        aria-label={`Quantité ${a.article_code}`}
                        value={quantities[a.article] ?? ''}
                        onChange={(e) => setQuantities({ ...quantities, [a.article]: e.target.value })}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <ErrorList messages={errors} />
        <div className="form-actions">
          <span>
            {lines.length} ligne(s) · {formatMoney(String(total))} HT
          </span>
          <button type="submit" disabled={lines.length === 0}>
            Enregistrer la commande
          </button>
        </div>
      </form>
    </section>
  )
}
