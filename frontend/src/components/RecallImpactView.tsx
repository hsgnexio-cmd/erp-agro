import { Link } from 'react-router'
import type { ImpactDelivery, ImpactLot, RecallImpact } from '../api/quality'
import { formatDate, formatDateTime, formatDecimal } from '../format'
import { type DataColumn, DataTable } from './DataTable'
import { StatusBadge } from './StatusBadge'

const LEVELS = ["Lot d'origine", 'Niveau 1', 'Niveau 2', 'Niveau 3', 'Niveau 4']

const DELIVERY_COLUMNS: DataColumn<ImpactDelivery>[] = [
  {
    id: 'customer',
    header: 'Enseigne',
    sortValue: (d) => d.customer_code,
    cell: (d) => `${d.customer_code} – ${d.customer_name}`,
  },
  {
    id: 'warehouse',
    header: 'Entrepôt',
    sortValue: (d) => d.warehouse_name,
    cell: (d) => (
      <>
        {d.warehouse_name} <small>({d.city})</small>
      </>
    ),
  },
  { id: 'lot', header: 'Lot', sortValue: (d) => d.lot_number, cell: (d) => d.lot_number },
  { id: 'article', header: 'Article', sortValue: (d) => d.article_code, cell: (d) => d.article_code },
  { id: 'expiry', header: 'DLC', sortValue: (d) => d.expiry_date, cell: (d) => formatDate(d.expiry_date) },
  {
    id: 'quantity',
    header: 'Quantité livrée',
    numeric: true,
    sortValue: (d) => Number(d.quantity),
    cell: (d) => `${formatDecimal(d.quantity)} ${d.unit}`,
  },
  {
    id: 'shipped',
    header: 'Dernière livraison',
    sortValue: (d) => d.last_shipped,
    cell: (d) => formatDate(d.last_shipped),
  },
]

/** Résultat d'un rappel : lots concernés, stocks restants, clients livrés. */
export function RecallImpactView({ impact }: { impact: RecallImpact }) {
  const finished = impact.lots.filter((lot) => lot.article_type === 'PF')
  // Sur la fiche d'un rappel lancé : lots bloqués par ce rappel (le statut affiché est celui d'avant)
  const blocked = new Set(impact.blocked_lots ?? [])

  const lotColumns: DataColumn<ImpactLot>[] = [
    {
      id: 'level',
      header: 'Niveau',
      sortValue: (lot) => lot.level,
      cell: (lot) => LEVELS[lot.level] ?? `Niveau ${lot.level}`,
    },
    {
      id: 'lot',
      header: 'Lot',
      sortValue: (lot) => lot.number,
      cell: (lot) => <Link to={`/lots/${lot.id}`}>{lot.number}</Link>,
    },
    {
      id: 'article',
      header: 'Article',
      sortValue: (lot) => lot.article_code,
      cell: (lot) => (
        <>
          {lot.article_code}
          <br />
          <small>{lot.article_name}</small>
        </>
      ),
    },
    {
      id: 'expiry',
      header: 'DLC / DDM',
      sortValue: (lot) => lot.expiry_date,
      cell: (lot) => formatDate(lot.expiry_date),
    },
    {
      id: 'status',
      header: 'Statut',
      sortValue: (lot) => lot.status_label,
      cell: (lot) => (
        <span className="wrap">
          <StatusBadge status={lot.status} label={lot.status_label} />
          {blocked.has(lot.number) && <span className="badge badge-danger">Bloqué par ce rappel</span>}
        </span>
      ),
    },
    {
      id: 'stock',
      header: 'Stock restant',
      numeric: true,
      sortValue: (lot) => Number(lot.stock_total),
      cell: (lot) =>
        lot.stock.length === 0
          ? '—'
          : lot.stock.map((row) => (
              <div key={row.location_code}>
                {formatDecimal(row.quantity)} {lot.unit} en {row.location_code}
              </div>
            )),
    },
  ]

  return (
    <>
      <div className="cards summary">
        <div className="card">
          <strong>{impact.lots.length}</strong>
          <span>lot(s) concerné(s), dont {finished.length} de produit fini</span>
        </div>
        <div className={impact.lots_to_block.length > 0 ? 'card card-danger' : 'card'}>
          <strong>{impact.lots_to_block.length}</strong>
          <span>lot(s) avec du stock {impact.blocked_lots ? 'bloqué(s)' : 'à bloquer'}</span>
        </div>
        <div className={impact.customers.length > 0 ? 'card card-danger' : 'card'}>
          <strong>{impact.customers.length}</strong>
          <span>enseigne(s) livrée(s) à prévenir</span>
        </div>
      </div>
      <p className="hint">Calculé le {formatDateTime(impact.computed_at)}.</p>

      <h2>Lots concernés et stocks restants</h2>
      <DataTable caption="Lots concernés" rows={impact.lots} rowKey={(lot) => lot.id} columns={lotColumns} />

      <h2>Clients livrés</h2>
      {impact.deliveries.length === 0 ? (
        <div className="empty-state">
          <strong>Aucune livraison</strong>
          <span>Rien n'est parti chez les clients.</span>
        </div>
      ) : (
        <DataTable
          caption="Clients livrés"
          rows={impact.deliveries}
          rowKey={(d) => `${d.warehouse_code}-${d.lot_number}`}
          columns={DELIVERY_COLUMNS}
        />
      )}
    </>
  )
}
