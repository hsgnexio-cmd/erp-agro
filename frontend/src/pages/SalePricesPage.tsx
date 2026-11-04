import { useState } from 'react'
import type { SalePrice } from '../api/sales'
import type { Customer, Paginated } from '../api/types'
import { formatDate, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

/** Tarifs de vente par enseigne (saisie dans l'administration). */
export function SalePricesPage() {
  const customers = useApi<Paginated<Customer>>('/api/referentiel/customers/')
  const [customer, setCustomer] = useState('')
  const prices = useApi<Paginated<SalePrice>>(
    `/api/ventes/prices/?customer=${customer}`,
  )

  return (
    <section>
      <h1>Tarifs de vente</h1>
      <p className="hint">
        Prix HT par enseigne et par produit. Les tarifs se saisissent dans l'administration
        (rôles commercial et admin).
      </p>
      <div className="filters">
        <select aria-label="Enseigne" value={customer} onChange={(e) => setCustomer(e.target.value)}>
          <option value="">Toutes les enseignes</option>
          {customers.data?.results.map((c) => (
            <option key={c.id} value={c.id}>
              {c.code} – {c.name}
            </option>
          ))}
        </select>
      </div>
      {prices.data && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Enseigne</th>
                <th>Produit</th>
                <th>Désignation</th>
                <th className="num">Prix HT</th>
                <th>Valable</th>
              </tr>
            </thead>
            <tbody>
              {prices.data.results.map((price) => (
                <tr key={price.id}>
                  <td>{price.customer_code}</td>
                  <td>{price.article_code}</td>
                  <td>{price.article_name}</td>
                  <td className="num">{formatDecimal(price.unit_price)} €</td>
                  <td>
                    du {formatDate(price.valid_from)}
                    {price.valid_to && ` au ${formatDate(price.valid_to)}`}
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
