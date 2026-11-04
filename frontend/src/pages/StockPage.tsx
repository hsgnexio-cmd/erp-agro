import { useState } from 'react'
import { Link } from 'react-router'
import type { Paginated, Site, StockSummaryRow } from '../api/types'
import { formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

const TYPES = [
  { value: '', label: 'Tous les types' },
  { value: 'MP', label: 'Matières premières' },
  { value: 'SF', label: 'Semi-finis' },
  { value: 'PF', label: 'Produits finis' },
  { value: 'EM', label: 'Emballages' },
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
      <p className="hint">
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
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Article</th>
                <th>Désignation</th>
                <th>Site</th>
                <th className="num">Libéré</th>
                <th className="num">Quarantaine</th>
                <th className="num">Bloqué</th>
                <th className="num">Total</th>
              </tr>
            </thead>
            <tbody>
              {data.length === 0 && (
                <tr>
                  <td colSpan={7}>Aucun stock.</td>
                </tr>
              )}
              {data.map((row) => (
                <tr key={`${row.article}-${row.site_code}`}>
                  <td>
                    <Link to={`/lots?search=${row.article_code}`}>{row.article_code}</Link>
                  </td>
                  <td>{row.article_name}</td>
                  <td>{row.site_code}</td>
                  <td className="num">{quantity(row.released, row.unit)}</td>
                  <td className="num">{quantity(row.quarantine, row.unit)}</td>
                  <td className="num">{quantity(row.blocked, row.unit)}</td>
                  <td className="num">
                    <strong>{quantity(row.total, row.unit)}</strong>
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

function quantity(value: string, unit: string): string {
  return Number(value) === 0 ? '—' : `${formatDecimal(value)} ${unit}`
}
