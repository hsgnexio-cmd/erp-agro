import { useState } from 'react'
import { useSearchParams } from 'react-router'
import type { Lot, Paginated } from '../api/types'
import { type DataColumn, DataTable } from '../components/DataTable'
import { LotDrawer } from '../components/LotDrawer'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

const STATUSES = [
  { value: '', label: 'Tous les statuts' },
  { value: 'quarantaine', label: 'Quarantaine' },
  { value: 'libere', label: 'Libéré' },
  { value: 'bloque', label: 'Bloqué' },
  { value: 'detruit', label: 'Détruit' },
]

/** Fichier CSV (séparateur « ; », lisible par Excel) des lots sélectionnés. */
function exportCsv(lots: Lot[]) {
  const header = ['Lot', 'Article', 'Désignation', 'DLC / DDM', 'Quantité', 'Unité', 'Emplacement', 'Statut']
  const rows = lots.map((lot) => [
    lot.number,
    lot.article_code,
    lot.article_name,
    lot.expiry_date ?? '',
    formatDecimal(lot.quantity),
    lot.unit,
    lot.location_code,
    lot.status_label,
  ])
  const text = [header, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(';'))
    .join('\r\n')
  const url = URL.createObjectURL(new Blob([`${String.fromCharCode(0xfeff)}${text}`], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = 'lots.csv'
  link.click()
  URL.revokeObjectURL(url)
}

export function LotsPage() {
  const [status, setStatus] = useState('')
  const [searchParams] = useSearchParams()
  const [search, setSearch] = useState(searchParams.get('search') ?? '')
  const [opened, setOpened] = useState<Lot | null>(null)
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (search) params.set('search', search)
  const { data, error } = useApi<Paginated<Lot>>(`/api/stocks/lots/?${params}`)

  const columns: DataColumn<Lot>[] = [
    {
      id: 'number',
      header: 'Lot',
      sortValue: (lot) => lot.number,
      cell: (lot) => (
        <button
          type="button"
          className="link-button lot-number"
          onClick={(event) => {
            event.stopPropagation()
            setOpened(lot)
          }}
        >
          {lot.number}
        </button>
      ),
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
      id: 'supplier_lot',
      header: 'Lot fournisseur',
      sortValue: (lot) => lot.supplier_lot_number,
      cell: (lot) => lot.supplier_lot_number || '—',
    },
    {
      id: 'reception',
      header: 'Reçu le',
      sortValue: (lot) => lot.reception_date,
      cell: (lot) => formatDate(lot.reception_date),
    },
    {
      id: 'expiry',
      header: 'DLC / DDM',
      sortValue: (lot) => lot.expiry_date,
      cell: (lot) => (lot.expiry_date ? `${formatDate(lot.expiry_date)} (${lot.date_type})` : '—'),
    },
    {
      id: 'quantity',
      header: 'Quantité',
      numeric: true,
      sortValue: (lot) => Number(lot.quantity),
      cell: (lot) => `${formatDecimal(lot.quantity)} ${lot.unit}`,
    },
    {
      id: 'location',
      header: 'Emplacement',
      sortValue: (lot) => lot.location_code,
      cell: (lot) => lot.location_code,
    },
    {
      id: 'status',
      header: 'Statut',
      sortValue: (lot) => lot.status_label,
      cell: (lot) => (
        <span className="wrap">
          <StatusBadge status={lot.status} label={lot.status_label} />
          {lot.block_reason && <small className="reason">{lot.block_reason}</small>}
        </span>
      ),
    },
  ]

  return (
    <section>
      <h1>Lots</h1>
      <p className="page-intro">
        Clique sur un lot pour ouvrir sa fiche et sa traçabilité sans quitter la liste. Seul un lot
        libéré peut être consommé ou expédié.
      </p>
      <div className="filters">
        <input
          type="search"
          placeholder="Rechercher un lot, un lot fournisseur ou un article"
          aria-label="Rechercher"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select aria-label="Statut" value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <p className="count">{data.count} lot(s)</p>
          <DataTable
            caption="Lots"
            rows={data.results}
            columns={columns}
            rowKey={(lot) => lot.id}
            onRowClick={setOpened}
            empty="Aucun lot ne correspond."
            bulkActions={[{ label: 'Exporter la sélection (CSV)', onRun: exportCsv }]}
          />
        </>
      )}
      <LotDrawer lot={opened} onClose={() => setOpened(null)} />
    </section>
  )
}
