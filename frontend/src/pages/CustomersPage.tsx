import { useState } from 'react'
import type { Customer, Paginated } from '../api/types'
import { type DataColumn, DataTable } from '../components/DataTable'
import { Drawer } from '../components/Drawer'
import { formatDecimal, yesNo } from '../format'
import { useApi } from '../hooks/useApi'

const COLUMNS: DataColumn<Customer>[] = [
  { id: 'code', header: 'Code', sortValue: (c) => c.code, cell: (c) => c.code },
  { id: 'name', header: 'Enseigne', sortValue: (c) => c.name, cell: (c) => c.name },
  {
    id: 'type',
    header: 'Type',
    sortValue: (c) => c.customer_type_label,
    cell: (c) => c.customer_type_label,
  },
  { id: 'brand', header: 'Marque Brévanne', cell: (c) => yesNo(c.sells_brand) },
  {
    id: 'mdd',
    header: 'MDD',
    cell: (c) =>
      c.sells_private_label ? <span className="badge badge-info">MDD</span> : yesNo(false),
  },
  {
    id: 'shelf_life',
    header: 'DLC mini à la livraison',
    numeric: true,
    sortValue: (c) => Number(c.min_remaining_shelf_life_pct),
    cell: (c) => `${formatDecimal(c.min_remaining_shelf_life_pct)} %`,
  },
  {
    id: 'warehouses',
    header: 'Entrepôts',
    numeric: true,
    sortValue: (c) => c.warehouse_count,
    cell: (c) => c.warehouse_count,
  },
]

export function CustomersPage() {
  const { data, error } = useApi<Paginated<Customer>>('/api/referentiel/customers/')
  const [opened, setOpened] = useState<Customer | null>(null)

  return (
    <section>
      <h1>Clients (enseignes)</h1>
      <p className="page-intro">
        Chaque enseigne fixe la part de durée de vie qui doit rester à la livraison : un lot trop
        court est bloqué pour elle. Clique sur une ligne pour voir sa fiche.
      </p>
      {error && <p className="error">{error}</p>}
      {data && (
        <DataTable
          caption="Enseignes"
          rows={data.results}
          columns={COLUMNS}
          rowKey={(customer) => customer.id}
          onRowClick={setOpened}
          empty="Aucune enseigne."
        />
      )}
      {opened && (
        <Drawer open onClose={() => setOpened(null)} title={opened.code} subtitle={opened.name}>
          <dl className="details drawer-details">
            <dt>Type</dt>
            <dd>{opened.customer_type_label}</dd>
            <dt>Vend la marque Brévanne</dt>
            <dd>{yesNo(opened.sells_brand)}</dd>
            <dt>Vend en marque distributeur</dt>
            <dd>{yesNo(opened.sells_private_label)}</dd>
            <dt>DLC minimale à la livraison</dt>
            <dd>{formatDecimal(opened.min_remaining_shelf_life_pct)} % de la durée de vie</dd>
            <dt>Entrepôts livrés</dt>
            <dd>{opened.warehouse_count}</dd>
            <dt>Active</dt>
            <dd>{opened.active ? 'Oui' : 'Non'}</dd>
          </dl>
          <p className="hint">
            Exemple : pour un produit à 14 jours de durée de vie, une enseigne à{' '}
            {formatDecimal(opened.min_remaining_shelf_life_pct)} % exige au moins{' '}
            {Math.ceil((14 * Number(opened.min_remaining_shelf_life_pct)) / 100)} jours restants à la
            livraison.
          </p>
        </Drawer>
      )}
    </section>
  )
}
