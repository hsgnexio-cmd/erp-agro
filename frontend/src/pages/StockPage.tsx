import { useState } from 'react'
import { Link } from 'react-router'
import type { Paginated, Site, StockSummaryRow } from '../api/types'
import { type DataColumn, DataTable } from '../components/DataTable'
import { formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

const TYPES = [
  { value: '', label: 'Tous les types' },
  { value: 'MP', label: 'Matières premières' },
  { value: 'SF', label: 'Semi-finis' },
  { value: 'PF', label: 'Produits finis' },
  { value: 'EM', label: 'Emballages' },
]

const amount = (
  key: 'released' | 'quarantine' | 'blocked' | 'total',
  header: string,
): DataColumn<StockSummaryRow> => ({
  id: key,
  header,
  numeric: true,
  sortValue: (row) => Number(row[key]),
  cell: (row) =>
    key === 'total' ? <strong>{quantity(row.total, row.unit)}</strong> : quantity(row[key], row.unit),
})

const COLUMNS: DataColumn<StockSummaryRow>[] = [
  {
    id: 'article',
    header: 'Article',
    sortValue: (row) => row.article_code,
    cell: (row) => <Link to={`/lots?search=${row.article_code}`}>{row.article_code}</Link>,
  },
  {
    id: 'name',
    header: 'Désignation',
    sortValue: (row) => row.article_name,
    cell: (row) => row.article_name,
  },
  { id: 'site', header: 'Site', sortValue: (row) => row.site_code, cell: (row) => row.site_code },
  amount('released', 'Libéré'),
  amount('quarantine', 'Quarantaine'),
  amount('blocked', 'Bloqué'),
  amount('total', 'Total'),
]

export function StockPage() {
  const sites = useApi<Paginated<Site>>('/api/referentiel/sites/')
  const [site, setSite] = useState('')
  const [articleType, setArticleType] = useState('')
  const [search, setSearch] = useState('')

  const params = new URLSearchParams()
  if (site) params.set('site', site)
  if (articleType) params.set('article_type', articleType)
  if (search) params.set('search', search)
  const { data, error } = useApi<StockSummaryRow[]>(`/api/stocks/summary/?${params}`)

  return (
    <section>
      <h1>État des stocks</h1>
      <p className="page-intro">
        Seul le stock <strong>libéré</strong> est utilisable en production et en expédition.
      </p>
      <div className="filters">
        <input
          type="search"
          placeholder="Rechercher un article"
          aria-label="Rechercher"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select aria-label="Site" value={site} onChange={(e) => setSite(e.target.value)}>
          <option value="">Tous les sites</option>
          {sites.data?.results.map((s) => (
            <option key={s.id} value={s.code}>
              {s.code} – {s.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Type d'article"
          value={articleType}
          onChange={(e) => setArticleType(e.target.value)}
        >
          {TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <DataTable
          caption="État des stocks par article et par site"
          rows={data}
          columns={COLUMNS}
          rowKey={(row) => `${row.article}-${row.site_code}`}
          empty="Aucun stock."
        />
      )}
    </section>
  )
}

function quantity(value: string, unit: string): string {
  return Number(value) === 0 ? '—' : `${formatDecimal(value)} ${unit}`
}
