import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import type { FefoPlan, Paginated, Site } from '../api/types'
import { formatDate, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

/** Outil FEFO : quels lots utiliser en premier pour un besoin donné ? (règle 4) */
export function FefoPage() {
  const sites = useApi<Paginated<Site>>('/api/referentiel/sites/')
  const [article, setArticle] = useState('')
  const [site, setSite] = useState('MPE')
  const [quantity, setQuantity] = useState('')
  const [query, setQuery] = useState<string | null>(null)
  const plan = useApi<FefoPlan>(query)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const params = new URLSearchParams({ article, site, quantity })
    setQuery(`/api/stocks/fefo/?${params}`)
  }

  return (
    <section>
      <h1>Proposition FEFO</h1>
      <p className="hint">
        First Expired, First Out : l'ERP propose toujours les lots libérés qui périment le premier.
      </p>
      <form className="form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label>
            Code article
            <input
              value={article}
              onChange={(e) => setArticle(e.target.value)}
              placeholder="MP-LAI-CREME35"
              required
            />
          </label>
          <label>
            Site
            <select value={site} onChange={(e) => setSite(e.target.value)}>
              {sites.data?.results.map((s) => (
                <option key={s.id} value={s.code}>
                  {s.code} – {s.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Quantité à servir
            <input
              type="number"
              min="0"
              step="any"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              required
            />
          </label>
        </div>
        <div className="form-actions">
          <button type="submit">Proposer les lots</button>
        </div>
      </form>

      {plan.error && <p className="error">{plan.error}</p>}
      {plan.data && (
        <>
          <h2>
            {plan.data.article_code} sur {plan.data.site_code}
          </h2>
          {Number(plan.data.missing) > 0 ? (
            <p className="error-box">
              Stock libéré insuffisant : il manque {formatDecimal(plan.data.missing)}{' '}
              {plan.data.unit}.
            </p>
          ) : (
            <p className="status status-ok">
              Besoin couvert : {formatDecimal(plan.data.covered)} {plan.data.unit}.
            </p>
          )}
          {plan.data.lines.length > 0 && (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Ordre</th>
                    <th>Lot</th>
                    <th>Péremption</th>
                    <th>Emplacement</th>
                    <th className="num">Disponible</th>
                    <th className="num">À prendre</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.data.lines.map((line, index) => (
                    <tr key={`${line.lot}-${line.location_code}`}>
                      <td>{index + 1}</td>
                      <td>
                        <Link to={`/lots/${line.lot}`}>{line.lot_number}</Link>
                      </td>
                      <td>
                        {line.expiry_date
                          ? `${formatDate(line.expiry_date)} (${line.date_type})`
                          : '—'}
                      </td>
                      <td>{line.location_code}</td>
                      <td className="num">
                        {formatDecimal(line.available)} {plan.data!.unit}
                      </td>
                      <td className="num">
                        <strong>
                          {formatDecimal(line.take)} {plan.data!.unit}
                        </strong>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  )
}
