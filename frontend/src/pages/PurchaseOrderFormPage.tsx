import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { CatalogItem, Paginated, PurchaseOrder, Site, Supplier } from '../api/types'
import { ErrorList } from '../components/ErrorList'
import { formatDecimal, formatMoney, todayIso } from '../format'
import { useApi } from '../hooks/useApi'

export function PurchaseOrderFormPage() {
  const navigate = useNavigate()
  // Seuls les fournisseurs actifs et audités peuvent être commandés
  const suppliers = useApi<Paginated<Supplier>>(
    '/api/referentiel/suppliers/?active=true&audited=true',
  )
  const sites = useApi<Paginated<Site>>('/api/referentiel/sites/?active=true')

  const [supplierId, setSupplierId] = useState('')
  const [siteId, setSiteId] = useState('')
  const [orderDate, setOrderDate] = useState(todayIso())
  const [comment, setComment] = useState('')
  const [quantities, setQuantities] = useState<Record<number, string>>({})
  const [errors, setErrors] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)

  const catalog = useApi<CatalogItem[]>(
    supplierId ? `/api/achats/catalog/?supplier=${supplierId}&date=${orderDate}` : null,
  )

  // Par défaut, livraison à l'entrepôt matières et emballages (MPE)
  const defaultSite = sites.data?.results.find((site) => site.code === 'MPE')
  const deliverySite = siteId || (defaultSite ? String(defaultSite.id) : '')

  const lines = (catalog.data ?? [])
    .filter((item) => Number(quantities[item.article]) > 0)
    .map((item) => ({ item, quantity: quantities[item.article] }))
  const total = lines.reduce(
    (sum, { item, quantity }) => sum + Number(quantity) * Number(item.unit_price ?? 0),
    0,
  )

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setErrors([])
    try {
      const order = await apiPost<PurchaseOrder>('/api/achats/orders/', {
        supplier: Number(supplierId),
        delivery_site: Number(deliverySite),
        order_date: orderDate,
        comment,
        lines: lines.map(({ item, quantity }) => ({ article: item.article, quantity })),
      })
      navigate(`/commandes/${order.id}`)
    } catch (error) {
      setErrors(errorMessages(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section>
      <p>
        <Link to="/commandes">← Retour aux commandes</Link>
      </p>
      <h1>Nouvelle commande fournisseur</h1>
      <form className="form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label>
            Fournisseur
            <select
              value={supplierId}
              onChange={(e) => {
                setSupplierId(e.target.value)
                setQuantities({})
              }}
              required
            >
              <option value="">— Choisir —</option>
              {suppliers.data?.results.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} – {s.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Site de livraison
            <select value={deliverySite} onChange={(e) => setSiteId(e.target.value)} required>
              {sites.data?.results.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.code} – {site.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Date de commande
            <input
              type="date"
              value={orderDate}
              onChange={(e) => setOrderDate(e.target.value)}
              required
            />
          </label>
          <label>
            Commentaire
            <input value={comment} onChange={(e) => setComment(e.target.value)} />
          </label>
        </div>

        {supplierId && catalog.data && (
          <>
            <h2>Articles du fournisseur</h2>
            <p className="hint">Saisis une quantité pour les articles à commander.</p>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Article</th>
                    <th>Désignation</th>
                    <th className="num">Prix HT</th>
                    <th className="num">Minimum</th>
                    <th className="num">Quantité</th>
                  </tr>
                </thead>
                <tbody>
                  {catalog.data.map((item) => (
                    <tr key={item.article}>
                      <td>{item.article_code}</td>
                      <td>{item.article_name}</td>
                      <td className="num">
                        {item.unit_price
                          ? `${formatDecimal(item.unit_price)} € / ${item.unit}`
                          : 'Pas de tarif'}
                      </td>
                      <td className="num">
                        {item.min_order_quantity
                          ? `${formatDecimal(item.min_order_quantity)} ${item.unit}`
                          : '—'}
                      </td>
                      <td className="num">
                        <input
                          type="number"
                          min="0"
                          step="any"
                          className="qty"
                          aria-label={`Quantité ${item.article_code}`}
                          value={quantities[item.article] ?? ''}
                          onChange={(e) =>
                            setQuantities({ ...quantities, [item.article]: e.target.value })
                          }
                        />{' '}
                        {item.unit}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        <ErrorList messages={errors} />
        <div className="form-actions">
          <span>
            {lines.length} ligne(s) · {formatMoney(String(total))} HT
          </span>
          <button type="submit" disabled={submitting || lines.length === 0}>
            Enregistrer en brouillon
          </button>
        </div>
      </form>
    </section>
  )
}
