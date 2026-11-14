import { ExternalLink } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import type { Article, Paginated } from '../api/types'
import { type DataColumn, DataTable } from '../components/DataTable'
import { Drawer } from '../components/Drawer'
import { formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

// Filtres rapides par type d'article
const TYPES = [
  { value: '', label: 'Tous' },
  { value: 'MP', label: 'Matières premières' },
  { value: 'SF', label: 'Semi-finis' },
  { value: 'PF', label: 'Produits finis' },
  { value: 'EM', label: 'Emballages' },
]

const TEMPERATURES: Record<string, string> = {
  froid_positif: 'Froid positif (0 à 4 °C)',
  froid_negatif: 'Froid négatif (-18 °C)',
  ambiant: 'Ambiant',
}

const shelfLife = (article: Article) =>
  article.shelf_life_days ? `${article.shelf_life_days} j (${article.date_type})` : '—'

const COLUMNS: DataColumn<Article>[] = [
  {
    id: 'code',
    header: 'Code',
    sortValue: (article) => article.code,
    cell: (article) => (
      <Link to={`/articles/${article.id}`} onClick={(event) => event.stopPropagation()}>
        {article.code}
      </Link>
    ),
  },
  {
    id: 'name',
    header: 'Désignation',
    sortValue: (article) => article.name,
    cell: (article) => article.name,
  },
  {
    id: 'type',
    header: 'Type',
    sortValue: (article) => article.article_type_label,
    cell: (article) => article.article_type_label,
  },
  { id: 'unit', header: 'Unité', cell: (article) => article.unit },
  {
    id: 'shelf_life',
    header: 'Durée de vie',
    numeric: true,
    sortValue: (article) => article.shelf_life_days,
    cell: shelfLife,
  },
  {
    id: 'allergens',
    header: 'Allergènes',
    cell: (article) => article.allergen_names.join(', ') || '—',
  },
]

/** Fiche d'un article dans le tiroir : ses spécifications clés. */
function ArticleDrawer({ article, onClose }: { article: Article | null; onClose: () => void }) {
  if (!article) return null
  return (
    <Drawer
      open
      onClose={onClose}
      title={article.code}
      subtitle={article.name}
      footer={
        <Link className="button secondary" to={`/articles/${article.id}`}>
          <ExternalLink size={15} aria-hidden="true" /> Fiche complète et nomenclature
        </Link>
      }
    >
      <dl className="details drawer-details">
        <dt>Type</dt>
        <dd>{article.article_type_label}</dd>
        <dt>Unité de stock</dt>
        <dd>{article.unit}</dd>
        <dt>Durée de vie</dt>
        <dd>{shelfLife(article)}</dd>
        <dt>Conservation</dt>
        <dd>{TEMPERATURES[article.storage_temperature_class] ?? article.storage_temperature_class}</dd>
        {article.category_code && (
          <>
            <dt>Catégorie</dt>
            <dd>{article.category_code}</dd>
          </>
        )}
        {article.recipe_code && (
          <>
            <dt>Recette</dt>
            <dd>
              {article.recipe_code}
              {article.brand_code && ` · marque ${article.brand_code}`}
              {article.format_size && ` · ${article.format_size} g`}
            </dd>
          </>
        )}
        {article.safety_stock_days && (
          <>
            <dt>Stock de sécurité</dt>
            <dd>{formatDecimal(article.safety_stock_days)} jour(s) de vente</dd>
          </>
        )}
        <dt>Allergènes</dt>
        <dd>{article.allergen_names.join(', ') || 'Aucun'}</dd>
        <dt>Nomenclature</dt>
        <dd>{article.has_bom ? 'Oui, voir la fiche complète' : 'Aucune'}</dd>
      </dl>
    </Drawer>
  )
}

export function ArticlesPage() {
  const [search, setSearch] = useState('')
  const [articleType, setArticleType] = useState('')
  const [page, setPage] = useState(1)
  const [opened, setOpened] = useState<Article | null>(null)

  const params = new URLSearchParams({ page: String(page) })
  if (search) params.set('search', search)
  if (articleType) params.set('article_type', articleType)
  const { data, error, loading } = useApi<Paginated<Article>>(
    `/api/referentiel/articles/?${params}`,
  )

  return (
    <section>
      <h1>Articles</h1>
      <p className="page-intro">
        Matières premières, semi-finis, produits finis et emballages. Clique sur une ligne pour voir
        ses spécifications.
      </p>
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
        <div className="chips" role="group" aria-label="Type d'article">
          {TYPES.map((type) => (
            <button
              key={type.value}
              type="button"
              className={articleType === type.value ? 'chip active' : 'chip'}
              aria-pressed={articleType === type.value}
              onClick={() => {
                setArticleType(type.value)
                setPage(1)
              }}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && !data && <p>Chargement…</p>}
      {data && (
        <>
          <p className="count">{data.count} article(s)</p>
          <DataTable
            caption="Articles"
            rows={data.results}
            columns={COLUMNS}
            rowKey={(article) => article.id}
            onRowClick={setOpened}
            empty="Aucun article ne correspond."
          />
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
      <ArticleDrawer article={opened} onClose={() => setOpened(null)} />
    </section>
  )
}
