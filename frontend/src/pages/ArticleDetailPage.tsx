import { Link, useParams } from 'react-router'
import type { Article, Bom, Paginated } from '../api/types'
import { TEMPERATURE_LABELS, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

export function ArticleDetailPage() {
  const { id } = useParams()
  const article = useApi<Article>(`/api/referentiel/articles/${id}/`)
  const boms = useApi<Paginated<Bom>>(
    article.data?.has_bom ? `/api/referentiel/boms/?article=${id}` : null,
  )

  if (article.error) return <p className="error">{article.error}</p>
  if (!article.data) return <p>Chargement…</p>

  const a = article.data
  const bom = boms.data?.results[0]
  const isRawMaterial = a.article_type === 'MP'

  return (
    <section>
      <p>
        <Link to="/articles">← Retour aux articles</Link>
      </p>
      <h1>
        {a.code} <small>{a.name}</small>
      </h1>
      {!a.active && <p className="badge badge-off">Inactif</p>}

      <dl className="details">
        <dt>Type</dt>
        <dd>{a.article_type_label}</dd>
        <dt>Unité de stock</dt>
        <dd>{a.unit}</dd>
        {a.category_code && (
          <>
            <dt>Catégorie</dt>
            <dd>{a.category_code}</dd>
          </>
        )}
        {a.recipe_code && (
          <>
            <dt>Recette</dt>
            <dd>{a.recipe_code}</dd>
            <dt>Marque</dt>
            <dd>{a.brand_code === 'BRE' ? 'Brévanne' : `MDD ${a.brand_code}`}</dd>
            <dt>Format</dt>
            <dd>{a.format_size} g</dd>
          </>
        )}
        <dt>Durée de vie</dt>
        <dd>{a.shelf_life_days ? `${a.shelf_life_days} jours (${a.date_type})` : 'Sans objet'}</dd>
        <dt>Conservation</dt>
        <dd>{TEMPERATURE_LABELS[a.storage_temperature_class] ?? a.storage_temperature_class}</dd>
        <dt>Allergènes</dt>
        <dd>
          {isRawMaterial
            ? a.allergen_names.join(', ') || 'Aucun'
            : 'Calculés à partir de la nomenclature (phase 5)'}
        </dd>
      </dl>

      {a.technical_sheet && (
        <>
          <h2>Fiche technique</h2>
          <p className="text-block">{a.technical_sheet}</p>
        </>
      )}
      {a.specifications && (
        <>
          <h2>Cahier des charges</h2>
          <p className="text-block">{a.specifications}</p>
        </>
      )}

      {bom && (
        <>
          <h2>Nomenclature</h2>
          <p>
            Pour {formatDecimal(bom.base_quantity)} {bom.article_unit} fabriqué(s) :
          </p>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Composant</th>
                  <th>Désignation</th>
                  <th className="num">Quantité nette</th>
                  <th>Unité</th>
                  <th className="num">Perte</th>
                  <th className="num">Quantité brute</th>
                </tr>
              </thead>
              <tbody>
                {bom.lines.map((line) => (
                  <tr key={line.id}>
                    <td>
                      <Link to={`/articles/${line.component}`}>{line.component_code}</Link>
                    </td>
                    <td>{line.component_name}</td>
                    <td className="num">{formatDecimal(line.quantity)}</td>
                    <td>{line.unit}</td>
                    <td className="num">{formatDecimal(line.loss_rate)} %</td>
                    <td className="num">{formatDecimal(line.gross_quantity)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
