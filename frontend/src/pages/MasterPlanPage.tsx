import { useState } from 'react'
import { Link } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { MasterPlan, MasterPlanItem, MasterPlanSummary, ProductionLine } from '../api/production'
import type { Article, Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { PRODUCTION_ROLES, hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { formatDate, formatDateTime, formatDecimal, todayIso } from '../format'
import { useApi } from '../hooks/useApi'

const DAY_NAMES = ['Lun.', 'Mar.', 'Mer.', 'Jeu.', 'Ven.']

/** Lundi de la semaine d'une date AAAA-MM-JJ, décalé de `weeks` semaines. */
function monday(isoDate: string, weeks = 0): string {
  const date = new Date(`${isoDate}T12:00:00`)
  const offset = (date.getDay() + 6) % 7
  date.setDate(date.getDate() - offset + weeks * 7)
  return date.toISOString().slice(0, 10)
}

const sum = (values: string[]) => values.reduce((total, value) => total + Number(value), 0)

/** Plan de production hebdomadaire : calcul, ajustements, gel à J-2 (samedi 12 h). */
export function MasterPlanPage() {
  const { user } = useAuth()
  const canEdit = hasRole(user, PRODUCTION_ROLES)
  const nextWeek = monday(todayIso(), 1)
  const [week, setWeek] = useState(nextWeek)
  const [version, setVersion] = useState(0)
  const [errors, setErrors] = useState<string[]>([])
  const [skipped, setSkipped] = useState<string[]>([])
  const [confirming, setConfirming] = useState<'compute' | 'freeze' | null>(null)
  const [busy, setBusy] = useState(false)

  const list = useApi<Paginated<MasterPlanSummary>>(`/api/production/master-plans/?week=${week}&v=${version}`)
  const summary = list.data?.results[0]
  const plan = useApi<MasterPlan>(summary ? `/api/production/master-plans/${summary.id}/?v=${version}` : null)
  const isFuture = week >= nextWeek
  const editable = canEdit && plan.data?.status === 'brouillon'

  async function run(action: () => Promise<unknown>) {
    setBusy(true)
    setErrors([])
    try {
      await action()
      setVersion((v) => v + 1)
    } catch (error) {
      setErrors(errorMessages(error))
    } finally {
      setBusy(false)
      setConfirming(null)
    }
  }

  const compute = () =>
    run(async () => {
      const result = await apiPost<MasterPlan>('/api/production/master-plans/compute/', { week })
      setSkipped(result.skipped ?? [])
    })
  const freeze = () => run(() => apiPost(`/api/production/master-plans/${plan.data!.id}/freeze/`))
  const post = (path: string, body: unknown) =>
    run(() => apiPost(`/api/production/master-plans/${plan.data!.id}/${path}/`, body))

  return (
    <section>
      <div className="page-title">
        <h1>Plan de production</h1>
        <div className="actions">
          <Link to="/planning">Planning des lignes</Link>
          <Link to="/previsions">Prévisions</Link>
        </div>
      </div>
      <p className="hint">
        Plan de la semaine à venir, calculé à partir de la prévision de vente : marque Brévanne sur
        stock (prévision + stock de sécurité − stock projeté au lundi), MDD à la commande (prévision
        ou commandes reçues, sans stock de sécurité). Quantités arrondies au colis de 12, réparties du
        lundi au vendredi. Le plan est figé le samedi à 12 h (J-2) : les ordres de fabrication sont
        alors créés.
      </p>
      <div className="filters">
        <button type="button" className="secondary" onClick={() => setWeek(monday(week, -1))}>
          ← Semaine précédente
        </button>
        <button type="button" className="secondary" onClick={() => setWeek(nextWeek)}>
          Semaine prochaine
        </button>
        <button type="button" className="secondary" onClick={() => setWeek(monday(week, 1))}>
          Semaine suivante →
        </button>
        <strong className="week-title">Semaine du {formatDate(week)}</strong>
      </div>
      <ErrorList messages={errors} />
      {skipped.length > 0 && (
        <div className="panel">
          <p>Produits écartés du calcul :</p>
          <ul>
            {skipped.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      )}
      {list.data && !summary && (
        <div className="panel">
          <p>Aucun plan pour cette semaine.</p>
          {canEdit && isFuture && (
            <button type="button" disabled={busy} onClick={() => void compute()}>
              Calculer le plan
            </button>
          )}
        </div>
      )}
      {plan.data && (
        <>
          <PlanHeader plan={plan.data} />
          {editable && (
            <div className="actions">
              {confirming === null && (
                <>
                  <button type="button" className="secondary" disabled={busy} onClick={() => setConfirming('compute')}>
                    Recalculer
                  </button>
                  <button type="button" disabled={busy} onClick={() => setConfirming('freeze')}>
                    Figer le plan
                  </button>
                </>
              )}
              {confirming === 'compute' && (
                <span className="inline-form" role="group" aria-label="Confirmer le recalcul">
                  Les ajustements faits à la main seront perdus.
                  <button type="button" disabled={busy} onClick={() => void compute()}>
                    Confirmer le recalcul
                  </button>
                  <button type="button" className="secondary" onClick={() => setConfirming(null)}>
                    Annuler
                  </button>
                </span>
              )}
              {confirming === 'freeze' && (
                <span className="inline-form" role="group" aria-label="Confirmer le gel">
                  Un OF planifié sera créé par produit et par jour ; le plan ne sera plus modifiable.
                  <button type="button" disabled={busy} onClick={() => void freeze()}>
                    Confirmer le gel
                  </button>
                  <button type="button" className="secondary" onClick={() => setConfirming(null)}>
                    Annuler
                  </button>
                </span>
              )}
            </div>
          )}
          <PlanTable
            plan={plan.data}
            editable={editable}
            onQuantity={(article, day, quantity) => void post('set-quantity', { article, day, quantity })}
            onLine={(article, line) => void post('set-line', { article, line })}
          />
          {editable && (
            <AddArticle
              plan={plan.data}
              onAdd={(article) => void post('add-article', { article })}
            />
          )}
          <LoadTable plan={plan.data} />
        </>
      )}
    </section>
  )
}

function PlanHeader({ plan }: { plan: MasterPlan }) {
  return (
    <p>
      <span className={`badge ${plan.status === 'fige' ? 'badge-ok' : 'badge-warn'}`}>
        {plan.status_label}
      </span>{' '}
      {plan.week_label} · prévision {plan.forecast_version ?? 'du moment (aucune version figée)'} ·
      calculé le {formatDateTime(plan.computed_at)}
      {plan.computed_by_name && ` par ${plan.computed_by_name}`}
      {plan.frozen_at &&
        ` · figé le ${formatDateTime(plan.frozen_at)}${plan.frozen_by_name ? ` par ${plan.frozen_by_name}` : ' (automatique)'}`}
    </p>
  )
}

function projectedTitle(item: MasterPlanItem): string {
  return (
    `Stock disponible ${formatDecimal(item.stock)} + OF à venir ${formatDecimal(item.open_orders)}` +
    ` − demande prévue d'ici lundi ${formatDecimal(item.demand_before)}`
  )
}

function demandTitle(item: MasterPlanItem): string {
  return (
    `Prévision ${formatDecimal(item.forecast_quantity)} ; commandes reçues ` +
    formatDecimal(item.ordered_quantity)
  )
}

function PlanTable(props: {
  plan: MasterPlan
  editable: boolean
  onQuantity: (article: number, day: string, quantity: string) => void
  onLine: (article: number, line: number) => void
}) {
  const { plan, editable, onQuantity, onLine } = props
  return (
    <div className="table-wrapper">
      <table className="master-plan">
        <thead>
          <tr>
            <th>Produit</th>
            <th>Ligne</th>
            <th className="num">Demande</th>
            <th className="num">Stock de sécurité</th>
            <th className="num">Stock projeté</th>
            <th className="num">Calculé</th>
            {plan.days.map((day, index) => (
              <th key={day} className="num">
                {DAY_NAMES[index]} {day.slice(8, 10)}/{day.slice(5, 7)}
              </th>
            ))}
            <th className="num">Total</th>
          </tr>
        </thead>
        <tbody>
          {plan.items.length === 0 && (
            <tr>
              <td colSpan={plan.days.length + 7}>Aucun produit à fabriquer.</td>
            </tr>
          )}
          {plan.items.map((item) => (
            <tr key={item.article}>
              <td title={item.article_name}>
                {item.article_code} <small className="badge badge-neutral">{item.brand}</small>
              </td>
              <td>
                {editable ? (
                  <LineSelect item={item} onChange={(line) => onLine(item.article, line)} />
                ) : (
                  item.line_code
                )}
              </td>
              <td className="num" title={demandTitle(item)}>
                {formatDecimal(item.demand)}
              </td>
              <td className="num" title={`${formatDecimal(item.safety_days)} jour(s) de demande`}>
                {formatDecimal(item.safety_stock)}
              </td>
              <td className="num" title={projectedTitle(item)}>
                {formatDecimal(item.projected_stock)}
              </td>
              <td className="num">{formatDecimal(item.proposed_quantity)}</td>
              {item.days.map((entry) => (
                <td
                  key={entry.day}
                  className={`num${entry.closed ? ' closed-day' : ''}`}
                  title={entry.closed ? `Usine fermée : ${entry.closed}` : undefined}
                >
                  {entry.closed && Number(entry.quantity) === 0 ? (
                    <small className="closed-label">{entry.closed}</small>
                  ) : editable ? (
                    <input
                      key={`${entry.day}-${entry.quantity}`}
                      type="number"
                      min="0"
                      step="12"
                      className="qty"
                      aria-label={`${item.article_code} ${entry.day}`}
                      defaultValue={Number(entry.quantity)}
                      onBlur={(e) => {
                        if (e.target.value !== '' && Number(e.target.value) !== Number(entry.quantity)) {
                          onQuantity(item.article, entry.day, e.target.value)
                        }
                      }}
                    />
                  ) : (
                    <>
                      {formatDecimal(entry.quantity)}
                      {entry.production_order && (
                        <small>
                          {' '}
                          <Link to={`/production/${entry.production_order}`}>
                            {entry.production_order_number}
                          </Link>
                        </small>
                      )}
                      {entry.deviation && (
                        <span className="badge badge-warn" title="Écart avec le plan figé">
                          {entry.deviation}
                        </span>
                      )}
                    </>
                  )}
                </td>
              ))}
              <td className="num">
                <strong>{sum(item.days.map((entry) => entry.quantity)).toLocaleString('fr-FR')}</strong>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Choix d'une ligne compatible (famille et format), chargées à la demande. */
function LineSelect({ item, onChange }: { item: MasterPlanItem; onChange: (line: number) => void }) {
  const [open, setOpen] = useState(false)
  const lines = useApi<Paginated<ProductionLine>>(
    open ? `/api/referentiel/production-lines/?article=${item.article}` : null,
  )
  if (!open) {
    return (
      <button type="button" className="link-button" onClick={() => setOpen(true)} title="Changer de ligne">
        {item.line_code}
      </button>
    )
  }
  return (
    <select
      aria-label={`Ligne de ${item.article_code}`}
      value={item.line}
      onChange={(e) => {
        onChange(Number(e.target.value))
        setOpen(false)
      }}
    >
      <option value={item.line}>{item.line_code}</option>
      {lines.data?.results
        .filter((line) => line.id !== item.line)
        .map((line) => (
          <option key={line.id} value={line.id}>
            {line.code} – {line.name}
          </option>
        ))}
    </select>
  )
}

function AddArticle({ plan, onAdd }: { plan: MasterPlan; onAdd: (article: number) => void }) {
  const articles = useApi<Paginated<Article>>('/api/referentiel/articles/?article_type=PF&active=true')
  const [article, setArticle] = useState('')
  const planned = new Set(plan.items.map((item) => item.article))
  const choices = articles.data?.results.filter((a) => !planned.has(a.id)) ?? []
  if (choices.length === 0) return null
  return (
    <div className="actions">
      <select aria-label="Produit à ajouter" value={article} onChange={(e) => setArticle(e.target.value)}>
        <option value="">Ajouter un produit au plan…</option>
        {choices.map((a) => (
          <option key={a.id} value={a.id}>
            {a.code} – {a.name}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="secondary"
        disabled={!article}
        onClick={() => {
          onAdd(Number(article))
          setArticle('')
        }}
      >
        Ajouter
      </button>
    </div>
  )
}

function LoadTable({ plan }: { plan: MasterPlan }) {
  if (plan.load.length === 0) return null
  return (
    <>
      <h2>Charge des lignes</h2>
      <p className="hint">
        Heures = quantité ÷ cadence de la ligne. Capacité : {formatDecimal(plan.capacity_hours)} h par
        jour (2 équipes).
      </p>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Ligne</th>
              {plan.days.map((day, index) => (
                <th key={day} className="num">
                  {DAY_NAMES[index]} {day.slice(8, 10)}/{day.slice(5, 7)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {plan.load.map((row) => (
              <tr key={row.line}>
                <td>{row.line_code}</td>
                {row.cells.map((cell) => (
                  <td key={cell.day} className={`num${cell.closed ? ' closed-day' : ''}`}>
                    {cell.closed && cell.hours === '0.0' ? (
                      <small className="closed-label">fermé</small>
                    ) : cell.overload ? (
                      <span className="badge badge-danger" title="Surcharge">
                        {formatDecimal(cell.hours)} h
                      </span>
                    ) : (
                      `${formatDecimal(cell.hours)} h`
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
