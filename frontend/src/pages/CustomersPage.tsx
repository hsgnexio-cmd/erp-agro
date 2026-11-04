import type { Customer, Paginated } from '../api/types'
import { formatDecimal, yesNo } from '../format'
import { useApi } from '../hooks/useApi'

export function CustomersPage() {
  const { data, error } = useApi<Paginated<Customer>>('/api/referentiel/customers/')

  return (
    <section>
      <h1>Clients (enseignes)</h1>
      {error && <p className="error">{error}</p>}
      {data && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Enseigne</th>
                <th>Type</th>
                <th>Marque Brévanne</th>
                <th>MDD</th>
                <th className="num">DLC mini à la livraison</th>
                <th className="num">Entrepôts</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((c) => (
                <tr key={c.id} className={c.active ? '' : 'inactive'}>
                  <td>{c.code}</td>
                  <td>{c.name}</td>
                  <td>{c.customer_type_label}</td>
                  <td>{yesNo(c.sells_brand)}</td>
                  <td>{yesNo(c.sells_private_label)}</td>
                  <td className="num">{formatDecimal(c.min_remaining_shelf_life_pct)} %</td>
                  <td className="num">{c.warehouse_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
