import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { ProductionLine, ProductionOrderDetail } from '../api/production'
import type { Article, Paginated, Site } from '../api/types'
import { ErrorList } from '../components/ErrorList'
import { todayIso } from '../format'
import { useApi } from '../hooks/useApi'

export function ProductionOrderFormPage() {
  const navigate = useNavigate()
  const finished = useApi<Paginated<Article>>('/api/referentiel/articles/?article_type=PF&active=true')
  const semiFinished = useApi<Paginated<Article>>(
    '/api/referentiel/articles/?article_type=SF&active=true',
  )
  const sites = useApi<Paginated<Site>>('/api/referentiel/sites/?site_type=usine')

  const [articleId, setArticleId] = useState('')
  const [quantity, setQuantity] = useState('')
  const [date, setDate] = useState(todayIso())
  const [lineId, setLineId] = useState('')
  const [siteId, setSiteId] = useState('')
  const [sequence, setSequence] = useState('1')
  const [comment, setComment] = useState('')
  const [errors, setErrors] = useState<string[]>([])

  const articles = [...(finished.data?.results ?? []), ...(semiFinished.data?.results ?? [])]
  const article = articles.find((a) => String(a.id) === articleId)
  const isFinished = article?.article_type === 'PF'
  // Seules les lignes qui acceptent la famille et le format de l'article sont proposées
  const lines = useApi<Paginated<ProductionLine>>(
    isFinished ? `/api/referentiel/production-lines/?article=${articleId}` : null,
  )

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors([])
    try {
      const order = await apiPost<ProductionOrderDetail>('/api/production/orders/', {
        article: Number(articleId),
        planned_quantity: quantity,
        planned_date: date,
        line: isFinished && lineId ? Number(lineId) : null,
        site: !isFinished && siteId ? Number(siteId) : null,
        sequence: Number(sequence),
        comment,
      })
      navigate(`/production/${order.id}`)
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  return (
    <section>
      <p>
        <Link to="/production">← Retour aux ordres de fabrication</Link>
      </p>
      <h1>Nouvel ordre de fabrication</h1>
      <form className="form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label>
            Article à fabriquer
            <select
              value={articleId}
              onChange={(e) => {
                setArticleId(e.target.value)
                setLineId('')
              }}
              required
            >
              <option value="">— Choisir —</option>
              <optgroup label="Produits finis">
                {finished.data?.results.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.code} – {a.name}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Semi-finis">
                {semiFinished.data?.results.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.code} – {a.name}
                  </option>
                ))}
              </optgroup>
            </select>
          </label>
          <label>
            Quantité ({article?.unit ?? '—'})
            <input
              type="number"
              min="0"
              step="any"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              required
            />
          </label>
          <label>
            Date prévue
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          </label>
          {article &&
            (isFinished ? (
              <label>
                Ligne
                <select value={lineId} onChange={(e) => setLineId(e.target.value)} required>
                  <option value="">— Choisir —</option>
                  {lines.data?.results.map((line) => (
                    <option key={line.id} value={line.id}>
                      {line.code} – {line.name} ({line.capacity_per_hour}/h)
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label>
                Usine (cuisine)
                <select value={siteId} onChange={(e) => setSiteId(e.target.value)} required>
                  <option value="">— Choisir —</option>
                  {sites.data?.results.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.code} – {s.name}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          <label>
            Ordre dans la journée
            <input
              type="number"
              min="1"
              value={sequence}
              onChange={(e) => setSequence(e.target.value)}
            />
          </label>
          <label>
            Commentaire
            <input value={comment} onChange={(e) => setComment(e.target.value)} />
          </label>
        </div>
        {isFinished && lines.data?.results.length === 0 && (
          <p className="error">Aucune ligne n'accepte cet article (famille ou format).</p>
        )}
        <ErrorList messages={errors} />
        <div className="form-actions">
          <button type="submit">Créer l'OF (planifié)</button>
        </div>
      </form>
    </section>
  )
}
