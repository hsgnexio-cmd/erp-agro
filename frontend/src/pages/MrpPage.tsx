import { Fragment, useState } from 'react'
import { Link } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { CreatedPurchaseOrder, Mrp, MrpArticle, MrpProposal } from '../api/mrp'
import { useAuth } from '../auth/context'
import { PURCHASING_ROLES, hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { formatDate, formatDecimal, formatMoney, todayIso } from '../format'
import { useApi } from '../hooks/useApi'

type Horizon = 'now' | 'all'

const keyOf = (p: MrpProposal) => `${p.article}-${p.week}`

function inDays(days: number): string {
  const date = new Date(`${todayIso()}T12:00:00`)
  date.setDate(date.getDate() + days)
  return date.toISOString().slice(0, 10)
}

/** Calcul des besoins : propositions d'achat sur 9 semaines, transformées en commandes brouillon. */
export function MrpPage() {
  const { user } = useAuth()
  const canBuy = hasRole(user, PURCHASING_ROLES)
  const [version, setVersion] = useState(0)
  const { data, error, loading } = useApi<Mrp>(`/api/achats/mrp/?v=${version}`)
  const [horizon, setHorizon] = useState<Horizon>('now')
  const [supplier, setSupplier] = useState('')
  const [selected, setSelected] = useState<Record<string, string>>({})
  const [opened, setOpened] = useState<number | null>(null)
  const [errors, setErrors] = useState<string[]>([])
  const [created, setCreated] = useState<CreatedPurchaseOrder[]>([])
  const [saving, setSaving] = useState(false)

  // « À commander maintenant » : en retard ou à passer dans les 7 jours
  const limit = inDays(7)
  const proposals = (data?.proposals ?? []).filter(
    (p) =>
      (horizon === 'all' || p.order_date === null || p.order_date <= limit) &&
      (supplier === '' || String(p.supplier) === supplier),
  )
  const suppliers = new Map<number, string>()
  data?.proposals.forEach((p) => {
    if (p.supplier) suppliers.set(p.supplier, `${p.supplier_code} – ${p.supplier_name}`)
  })
  const chosen = (data?.proposals ?? []).filter((p) => keyOf(p) in selected)
  const total = chosen.reduce((sum, p) => sum + Number(p.unit_price ?? 0) * Number(selected[keyOf(p)]), 0)
  const lateCount = data?.proposals.filter((p) => p.late).length ?? 0

  function toggle(p: MrpProposal) {
    setSelected((current) => {
      const next = { ...current }
      if (keyOf(p) in next) delete next[keyOf(p)]
      else next[keyOf(p)] = String(Number(p.quantity))
      return next
    })
  }

  async function createOrders() {
    setSaving(true)
    setErrors([])
    try {
      const result = await apiPost<CreatedPurchaseOrder[]>('/api/achats/mrp/create-orders/', {
        selections: chosen.map((p) => ({ article: p.article, week: p.week, quantity: selected[keyOf(p)] })),
      })
      setCreated(result)
      setSelected({})
      setVersion((v) => v + 1)
    } catch (err) {
      setErrors(errorMessages(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section>
      <div className="page-title">
        <h1>Besoins d'achat</h1>
        <div className="actions">
          <Link to="/commandes">Commandes fournisseurs</Link>
          <Link to="/plan-production">Plan de production</Link>
        </div>
      </div>
      <p className="hint">
        Calcul des besoins (MRP) sur la semaine en cours et les 8 suivantes : production prévue (OF,
        plan, prévision de vente) éclatée en matières et emballages, pertes comprises, moins le stock
        disponible et les commandes fournisseurs en cours (brouillons compris). Une proposition est
        datée « besoin − délai du fournisseur » et relevée au minimum de commande ; l'acheteur choisit
        les propositions à transformer en commandes brouillon, qu'il vérifie puis envoie.
      </p>
      {loading && <p>Calcul en cours…</p>}
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <div className="table-wrapper">
            <table aria-label="Origine de la production prévue">
              <thead>
                <tr>
                  {data.weeks.map((w) => (
                    <th key={w.week}>
                      {w.label} <small>{formatDate(w.week).slice(0, 5)}</small>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  {data.weeks.map((w) => (
                    <td key={w.week}>
                      <small>{w.source}</small>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>

          <div className="filters">
            <select aria-label="Horizon" value={horizon} onChange={(e) => setHorizon(e.target.value as Horizon)}>
              <option value="now">À commander d'ici 7 jours (et en retard)</option>
              <option value="all">Toutes les propositions (9 semaines)</option>
            </select>
            <select aria-label="Fournisseur" value={supplier} onChange={(e) => setSupplier(e.target.value)}>
              <option value="">Tous les fournisseurs</option>
              {[...suppliers.entries()].map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
            {lateCount > 0 && <span className="badge badge-danger">{lateCount} en retard</span>}
          </div>

          <ErrorList messages={errors} />
          {created.length > 0 && (
            <div className="panel" role="status">
              <p>Commandes brouillon créées, à vérifier puis envoyer :</p>
              <ul>
                {created.map((order) => (
                  <li key={order.id}>
                    <Link to={`/commandes/${order.id}`}>{order.number}</Link> – {order.supplier_code},{' '}
                    {order.line_count} ligne(s), livraison prévue le {formatDate(order.expected_delivery_date)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {canBuy && (
            <div className="actions">
              <button type="button" disabled={chosen.length === 0 || saving} onClick={() => void createOrders()}>
                Créer les commandes brouillon ({chosen.length})
              </button>
              {chosen.length > 0 && <span>Montant estimé : {formatMoney(String(total))}</span>}
            </div>
          )}

          <div className="table-wrapper">
            <table aria-label="Propositions d'achat">
              <thead>
                <tr>
                  {canBuy && <th />}
                  <th>Article</th>
                  <th>Fournisseur</th>
                  <th>Besoin</th>
                  <th>Commander le</th>
                  <th className="num">Besoin net</th>
                  <th className="num">Quantité proposée</th>
                  <th className="num">Prix</th>
                  <th className="num">Montant</th>
                </tr>
              </thead>
              <tbody>
                {proposals.length === 0 && (
                  <tr>
                    <td colSpan={canBuy ? 9 : 8}>Aucune proposition sur cet horizon.</td>
                  </tr>
                )}
                {proposals.map((p) => (
                  <Fragment key={keyOf(p)}>
                    <tr className={p.late ? 'late' : undefined}>
                      {canBuy && (
                        <td>
                          <input
                            type="checkbox"
                            aria-label={`Sélectionner ${p.article_code} ${p.week_label}`}
                            checked={keyOf(p) in selected}
                            disabled={!p.supplier}
                            onChange={() => toggle(p)}
                          />
                        </td>
                      )}
                      <td title={p.article_name}>
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => setOpened(opened === p.article ? null : p.article)}
                        >
                          {p.article_code}
                        </button>
                      </td>
                      <td>
                        {p.supplier_code ? (
                          <>
                            {p.supplier_code} <small>({p.lead_time_days} j)</small>
                          </>
                        ) : (
                          <span className="badge badge-danger">aucun fournisseur audité</span>
                        )}
                      </td>
                      <td>
                        {p.week_label} <small>{formatDate(p.need_date)}</small>
                      </td>
                      <td>
                        {formatDate(p.order_date)}{' '}
                        {p.late && <span className="badge badge-danger">en retard</span>}
                      </td>
                      <td className="num">
                        {formatDecimal(p.net)} {p.unit}
                      </td>
                      <td className="num">
                        {keyOf(p) in selected ? (
                          <input
                            type="number"
                            min="0"
                            className="qty"
                            aria-label={`Quantité ${p.article_code} ${p.week_label}`}
                            value={selected[keyOf(p)]}
                            onChange={(e) => setSelected({ ...selected, [keyOf(p)]: e.target.value })}
                          />
                        ) : (
                          `${formatDecimal(p.quantity)} ${p.unit}`
                        )}
                        {p.raised_to_minimum && (
                          <small className="badge badge-info" title={`Minimum de commande : ${formatDecimal(p.min_order_quantity)}`}>
                            minimum
                          </small>
                        )}
                      </td>
                      <td className="num">{p.unit_price ? formatMoney(p.unit_price) : '—'}</td>
                      <td className="num">{formatMoney(p.amount)}</td>
                    </tr>
                    {opened === p.article && (
                      <tr>
                        <td colSpan={canBuy ? 9 : 8}>
                          <ArticleDetail
                            article={data.articles.find((a) => a.article === p.article)}
                            weeks={data.weeks.map((w) => w.label)}
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}

/** Calcul semaine par semaine d'un article : besoin brut, à recevoir, proposé, stock projeté. */
function ArticleDetail({ article, weeks }: { article: MrpArticle | undefined; weeks: string[] }) {
  if (!article) return null
  const rows: [string, keyof MrpArticle['weeks'][number]][] = [
    ['Besoin brut', 'gross'],
    ['À recevoir (commandes en cours)', 'receipts'],
    ['Proposé', 'planned'],
    ['Stock projeté en fin de semaine', 'projected'],
  ]
  return (
    <table aria-label={`Détail du calcul ${article.article_code}`}>
      <caption>
        {article.article_code} – {article.article_name} · stock disponible {formatDecimal(article.stock)}{' '}
        {article.unit}
      </caption>
      <thead>
        <tr>
          <th />
          {weeks.map((label) => (
            <th key={label} className="num">
              {label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map(([label, field]) => (
          <tr key={field}>
            <th>{label}</th>
            {article.weeks.map((cell) => (
              <td key={cell.week} className={`num${field === 'projected' && Number(cell.projected) < 0 ? ' negative' : ''}`}>
                {formatDecimal(cell[field])}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
