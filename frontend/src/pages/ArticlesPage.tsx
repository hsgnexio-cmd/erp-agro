import { useState } from 'react'
import { Link } from 'react-router'
import type { Article, Paginated } from '../api/types'
import { useApi } from '../hooks/useApi'

const TYPES = [
  { value: '', label: 'Tous les types' },
  { value: 'MP', label: 'Matières premières' },
  { value: 'SF', label: 'Semi-finis' },
  { value: 'PF', label: 'Produits finis' },
  { value: 'EM', label: 'Emballages' },
]

export function ArticlesPage() {
  const [search, setSearch] = useState('')
  const [articleType, setArticleType] = useState('')
  const [page, setPage] = useState(1)

  const params = new URLSearchParams({ page: String(page) })
  if (search) params.set('search', search)
  if (articleType) params.set('article_type', articleType)
  const { data, error, loading } = useApi<Paginated<Article>>(
    `/api/referentiel/articles/?${params}`,
  )

  return (
    <section>
      <h1>Articles</h1>
      <div className="filters">
        <input
          type="search"
          placeholder="Rechercher un code ou une désignation"
          aria-label="Rechercher"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
        />
        <select
          aria-label="Type d'article"
          value={articleType}
          onChange={(e) => {
            setArticleType(e.target.value)
            setPage(1)
          }}
        >
          {TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && !data && <p>Chargement…</p>}
      {data && (
        <>
          <p className="count">{data.count} article(s)</p>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Désignation</th>
                  <th>Type</th>
                  <th>Unité</th>
                  <th>Durée de vie</th>
                  <th>Allergènes</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((article) => (
                  <tr key={article.id} className={article.active ? '' : 'inactive'}>
                    <td>
                      <Link to={`/articles/${article.id}`}>{article.code}</Link>
                    </td>
                    <td>{article.name}</td>
                    <td>{article.article_type_label}</td>
                    <td>{article.unit}</td>
                    <td>
                      {article.shelf_life_days
                        ? `${article.shelf_life_days} j (${article.date_type})`
                        : '—'}
                    </td>
                    <td>{article.allergen_names.join(', ') || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <button type="button" disabled={!data.previous} onClick={() => setPage(page - 1)}>
              ← Précédent
            </button>
            <span>Page {page}</span>
            <button type="button" disabled={!data.next} onClick={() => setPage(page + 1)}>
              Suivant →
            </button>
          </div>
        </>
      )}
    </section>
  )
}
