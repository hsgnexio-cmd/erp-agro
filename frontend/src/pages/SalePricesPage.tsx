import { useState } from 'react'
import type { SalePrice } from '../api/sales'
import type { Customer, Paginated } from '../api/types'
import { type DataColumn, DataTable } from '../components/DataTable'
import { formatDate, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

const COLUMNS: DataColumn<SalePrice>[] = [
  {
    id: 'customer',
    header: 'Enseigne',
    sortValue: (price) => price.customer_code,
    cell: (price) => price.customer_code,
  },
  {
    id: 'article',
    header: 'Produit',
    sortValue: (price) => price.article_code,
    cell: (price) => price.article_code,
  },
  {
    id: 'name',
    header: 'Désignation',
    sortValue: (price) => price.article_name,
    cell: (price) => price.article_name,
  },
  {
    id: 'price',
    header: 'Prix HT',
    numeric: true,
    sortValue: (price) => Number(price.unit_price),
    cell: (price) => `${formatDecimal(price.unit_price)} €`,
  },
  {
    id: 'valid',
    header: 'Valable',
    sortValue: (price) => price.valid_from,
    cell: (price) => (
      <>
        du {formatDate(price.valid_from)}
        {price.valid_to && ` au ${formatDate(price.valid_to)}`}
      </>
    ),
  },
]

/** Tarifs de vente par enseigne (saisie dans l'administration). */
export function SalePricesPage() {
  const customers = useApi<Paginated<Customer>>('/api/referentiel/customers/')
  const [customer, setCustomer] = useState('')
  const prices = useApi<Paginated<SalePrice>>(`/api/ventes/prices/?customer=${customer}`)

  return (
    <section>
      <h1>Tarifs de vente</h1>
      <p className="page-intro">
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
      {prices.error && <p className="error">{prices.error}</p>}
      {prices.data && (
        <>
          <p className="count">{prices.data.count} tarif(s)</p>
          <DataTable
            caption="Tarifs de vente"
            rows={prices.data.results}
            columns={COLUMNS}
            rowKey={(price) => price.id}
            empty="Aucun tarif pour cette enseigne."
          />
        </>
      )}
    </section>
  )
}
