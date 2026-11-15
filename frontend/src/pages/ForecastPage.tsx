import { useState } from 'react'
import type { FormEvent } from 'react'
import { apiPost, errorMessages } from '../api/client'
import type {
  Accuracy,
  Forecast,
  ForecastCell,
  ForecastRow,
  ForecastVersion,
  ForecastWeek,
  Promotion,
} from '../api/forecast'
import type { Customer, Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { SALES_ROLES, hasRole } from '../auth/roles'
import { type DataColumn, DataTable } from '../components/DataTable'
import { ErrorList } from '../components/ErrorList'
import { formatDate, formatDateTime, formatDecimal, todayIso } from '../format'
import { useApi } from '../hooks/useApi'

interface CellKey {
  customer: number
  article: number
  week: string
}

const sameCell = (a: CellKey | null, b: CellKey) =>
  a !== null && a.customer === b.customer && a.article === b.article && a.week === b.week

/** Détail d'une case, lu au survol et par les lecteurs d'écran. */
function cellTitle(cell: ForecastCell): string {
  const parts = [`Calculé : ${formatDecimal(cell.base)}`]
  if (cell.promo_coefficient) {
    parts.push(`promotion ×${formatDecimal(cell.promo_coefficient)} : ${formatDecimal(cell.promo_quantity)}`)
  }
  if (cell.adjustment) {
    parts.push(`corrigé à ${formatDecimal(cell.adjustment.quantity)} (${cell.adjustment.reason})`)
  }
  return parts.join(' ; ')
}

/** Prévisions de vente à 8 semaines : grille, corrections, promotions, fiabilité, versions. */
export function ForecastPage() {
  const { user } = useAuth()
  const canEdit = hasRole(user, SALES_ROLES)
  const customers = useApi<Paginated<Customer>>('/api/referentiel/customers/')
  const [customer, setCustomer] = useState('')
  const [version, setVersion] = useState(0)
  const reload = () => setVersion((v) => v + 1)
  const forecast = useApi<Forecast>(`/api/previsions/forecast/?customer=${customer}&v=${version}`)
  const [selected, setSelected] = useState<CellKey | null>(null)
  const [showEmpty, setShowEmpty] = useState(false)

  // Produits jamais commandés par l'enseigne : prévision nulle, masqués par défaut
  const hasForecast = (row: ForecastRow) =>
    row.cells.some((cell) => Number(cell.quantity) > 0 || cell.adjustment || cell.promotion)
  const visibleRows = forecast.data?.rows.filter((row) => showEmpty || hasForecast(row)) ?? []
  const hiddenCount = (forecast.data?.rows.length ?? 0) - visibleRows.length

  const selectedRow = forecast.data?.rows.find(
    (row) => selected && row.customer === selected.customer && row.article === selected.article,
  )
  const selectedCell = selectedRow?.cells.find((cell) => cell.week === selected?.week)

  return (
    <section>
      <h1>Prévisions de vente</h1>
      <p className="hint">
        Demande prévue (quantités commandées) par produit et par enseigne, pour les semaines S+1 à
        S+8. Calcul : moyenne pondérée des 4 dernières semaines (40 %, 30 %, 20 %, 10 %), hors effet
        des promotions, arrondie au colis de 12 ; une promotion multiplie la quantité ; une
        correction du commercial la remplace. La prévision est figée chaque lundi à 5 h.
      </p>
      <div className="filters">
        <select
          aria-label="Enseigne"
          value={customer}
          onChange={(e) => {
            setCustomer(e.target.value)
            setSelected(null)
          }}
        >
          <option value="">Toutes les enseignes</option>
          {customers.data?.results.map((c) => (
            <option key={c.id} value={c.id}>
              {c.code} – {c.name}
            </option>
          ))}
        </select>
        <label className="checkbox-inline">
          <input type="checkbox" checked={showEmpty} onChange={(e) => setShowEmpty(e.target.checked)} />
          Afficher les produits sans prévision
          {!showEmpty && hiddenCount > 0 && <small> ({hiddenCount} masqués)</small>}
        </label>
      </div>
      {forecast.error && <p className="error">{forecast.error}</p>}
      {forecast.data && (
        <>
          <p className="legend">
            <span className="forecast-cell is-promo">×2</span> promotion
            <span className="forecast-cell is-adjusted">✎</span> correction manuelle
            {canEdit && <> · Clique sur une quantité pour la corriger.</>}
          </p>
          <ForecastGrid
            data={{ ...forecast.data, rows: visibleRows }}
            showCustomer={customer === ''}
            canEdit={canEdit}
            selected={selected}
            onSelect={setSelected}
          />
          {canEdit && selectedRow && selectedCell && (
            <AdjustmentForm
              key={`${selectedRow.customer}-${selectedRow.article}-${selectedCell.week}-${version}`}
              row={selectedRow}
              cell={selectedCell}
              week={forecast.data.weeks.find((w) => w.week === selectedCell.week)}
              onDone={reload}
              onClose={() => setSelected(null)}
            />
          )}
          {canEdit && <FreezeForm onDone={reload} />}
          <PromotionsSection
            customer={customer}
            customers={customers.data?.results ?? []}
            rows={forecast.data.rows}
            weeks={forecast.data.weeks}
            currentWeek={forecast.data.current_week}
            canEdit={canEdit}
            version={version}
            onChange={reload}
          />
        </>
      )}
      <AccuracySection customer={customer} version={version} />
      <VersionsSection version={version} />
    </section>
  )
}

// --- Grille -----------------------------------------------------------------------------

function ForecastGrid(props: {
  data: Forecast
  showCustomer: boolean
  canEdit: boolean
  selected: CellKey | null
  onSelect: (key: CellKey) => void
}) {
  const { data, showCustomer, canEdit, selected, onSelect } = props
  const totals = data.weeks.map((_, index) =>
    data.rows.reduce((sum, row) => sum + Number(row.cells[index].quantity), 0),
  )
  return (
    <div className="table-wrapper">
      <table className="forecast-grid">
        <thead>
          <tr>
            {showCustomer && <th>Enseigne</th>}
            <th>Produit</th>
            {data.weeks.map((week) => (
              <th key={week.week} className="num" title={`Semaine du ${formatDate(week.week)}`}>
                {week.label}
                <small> {formatDate(week.week).slice(0, 5)}</small>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.length === 0 && (
            <tr>
              <td colSpan={data.weeks.length + 2}>Aucun produit avec une prévision.</td>
            </tr>
          )}
          {data.rows.map((row) => (
            <tr key={`${row.customer}-${row.article}`}>
              {showCustomer && <td>{row.customer_code}</td>}
              <td title={row.article_name}>{row.article_code}</td>
              {row.cells.map((cell) => {
                const key = { customer: row.customer, article: row.article, week: cell.week }
                const classes = [
                  'num',
                  'forecast-cell',
                  cell.promo_coefficient ? 'is-promo' : '',
                  cell.adjustment ? 'is-adjusted' : '',
                  sameCell(selected, key) ? 'is-selected' : '',
                ].join(' ')
                const content = (
                  <>
                    {formatDecimal(cell.quantity)}
                    {cell.promo_coefficient && (
                      <small> ×{formatDecimal(cell.promo_coefficient)}</small>
                    )}
                    {cell.adjustment && <small> ✎</small>}
                  </>
                )
                return (
                  <td key={cell.week} className={classes} title={cellTitle(cell)}>
                    {canEdit ? (
                      <button
                        type="button"
                        className="cell-button"
                        aria-label={`${row.customer_code} ${row.article_code} ${cell.week} : ${cell.quantity}`}
                        onClick={() => onSelect(key)}
                      >
                        {content}
                      </button>
                    ) : (
                      content
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
        {data.rows.length > 0 && (
          <tfoot>
            <tr>
              <th colSpan={showCustomer ? 2 : 1}>Total</th>
              {totals.map((total, index) => (
                <th key={data.weeks[index].week} className="num">
                  {total.toLocaleString('fr-FR')}
                </th>
              ))}
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  )
}

// --- Correction manuelle ---------------------------------------------------------------

function AdjustmentForm(props: {
  row: ForecastRow
  cell: ForecastCell
  week: ForecastWeek | undefined
  onDone: () => void
  onClose: () => void
}) {
  const { row, cell, week, onDone, onClose } = props
  const [quantity, setQuantity] = useState(String(Number(cell.quantity)))
  const [reason, setReason] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [saving, setSaving] = useState(false)

  async function save(value: string | null) {
    setSaving(true)
    setErrors([])
    try {
      await apiPost('/api/previsions/adjustments/', {
        customer: row.customer,
        article: row.article,
        week: cell.week,
        quantity: value,
        reason,
      })
      onDone()
    } catch (error) {
      setErrors(errorMessages(error))
    } finally {
      setSaving(false)
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    void save(quantity)
  }

  return (
    <form className="panel form" onSubmit={submit} aria-label="Correction de la prévision">
      <h2>
        Corriger {row.article_code} – {row.customer_code} – {week?.label ?? cell.week}
      </h2>
      <p className="hint">
        Calculé : {formatDecimal(cell.base)}
        {cell.promo_coefficient &&
          ` ; promotion ×${formatDecimal(cell.promo_coefficient)} : ${formatDecimal(cell.promo_quantity)}`}
        {cell.adjustment &&
          ` ; corrigé à ${formatDecimal(cell.adjustment.quantity)} par ${cell.adjustment.created_by_name || '—'} le ${formatDateTime(cell.adjustment.created_at)} (« ${cell.adjustment.reason} »)`}
        . La correction remplace la quantité calculée ; elle est gardée dans le journal.
      </p>
      <ErrorList messages={errors} />
      <div className="form-grid">
        <label>
          Quantité prévue (unités)
          <input
            type="number"
            min="0"
            step="1"
            className="qty"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            required
          />
        </label>
        <label>
          Motif
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Ex. référencement dans 20 nouveaux magasins"
          />
        </label>
      </div>
      <div className="form-actions">
        <button type="button" className="secondary" onClick={onClose}>
          Fermer
        </button>
        {cell.adjustment && (
          <button type="button" className="secondary" disabled={saving} onClick={() => void save(null)}>
            Revenir au calcul
          </button>
        )}
        <button type="submit" disabled={saving}>
          Enregistrer la correction
        </button>
      </div>
    </form>
  )
}

// --- Version figée à la demande ----------------------------------------------------------

function FreezeForm({ onDone }: { onDone: () => void }) {
  const [comment, setComment] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setErrors([])
    try {
      const created = await apiPost<ForecastVersion>('/api/previsions/versions/', { comment })
      setMessage(`Version ${created.number} figée (${created.line_count} lignes).`)
      setComment('')
      onDone()
    } catch (error) {
      setErrors(errorMessages(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="actions" onSubmit={submit} aria-label="Figer une version">
      <input
        type="text"
        aria-label="Commentaire de la version"
        placeholder="Commentaire (facultatif)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
      />
      <button type="submit" disabled={saving}>
        Figer une version
      </button>
      {message && <span className="status status-ok">{message}</span>}
      <ErrorList messages={errors} />
    </form>
  )
}

// --- Promotions ------------------------------------------------------------------------

function promotionState(promotion: Promotion, currentWeek: string): { label: string; badge: string } {
  if (promotion.cancelled_at) return { label: 'Annulée', badge: 'badge-off' }
  if (promotion.last_week < currentWeek) return { label: 'Terminée', badge: 'badge-neutral' }
  if (promotion.first_week <= currentWeek) return { label: 'En cours', badge: 'badge-ok' }
  return { label: 'Prévue', badge: 'badge-info' }
}

function PromotionsSection(props: {
  customer: string
  customers: Customer[]
  rows: ForecastRow[]
  weeks: ForecastWeek[]
  currentWeek: string
  canEdit: boolean
  version: number
  onChange: () => void
}) {
  const { customer, customers, rows, weeks, currentWeek, canEdit, version, onChange } = props
  const promotions = useApi<Paginated<Promotion>>(
    `/api/previsions/promotions/?customer=${customer}&v=${version}`,
  )
  const [cancelling, setCancelling] = useState<number | null>(null)
  const [reason, setReason] = useState('')
  const [errors, setErrors] = useState<string[]>([])

  async function cancel(promotion: Promotion) {
    setErrors([])
    try {
      await apiPost(`/api/previsions/promotions/${promotion.id}/cancel/`, { reason })
      setCancelling(null)
      setReason('')
      onChange()
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  const promotionColumns: DataColumn<Promotion>[] = [
    {
      id: 'customer',
      header: 'Enseigne',
      sortValue: (promotion) => promotion.customer_code,
      cell: (promotion) => promotion.customer_code,
    },
    {
      id: 'article',
      header: 'Produit',
      sortValue: (promotion) => promotion.article_code,
      cell: (promotion) => <span title={promotion.article_name}>{promotion.article_code}</span>,
    },
    {
      id: 'weeks',
      header: 'Semaines',
      sortValue: (promotion) => promotion.first_week,
      cell: (promotion) => (
        <>
          {promotion.first_week_label}
          {promotion.last_week !== promotion.first_week && ` à ${promotion.last_week_label}`}
        </>
      ),
    },
    {
      id: 'coefficient',
      header: 'Coefficient',
      numeric: true,
      sortValue: (promotion) => Number(promotion.coefficient),
      cell: (promotion) => `×${formatDecimal(promotion.coefficient)}`,
    },
    {
      id: 'announced',
      header: 'Annoncée le',
      sortValue: (promotion) => promotion.announced_on,
      cell: (promotion) => (
        <>
          {formatDate(promotion.announced_on)}{' '}
          {promotion.late_notice && (
            <span className="badge badge-warn">annoncée tard ({promotion.notice_days} j avant)</span>
          )}
        </>
      ),
    },
    {
      id: 'status',
      header: 'Statut',
      sortValue: (promotion) => promotionState(promotion, currentWeek).label,
      cell: (promotion) => {
        const state = promotionState(promotion, currentWeek)
        return (
          <>
            <span className={`badge ${state.badge}`}>{state.label}</span>
            {promotion.cancel_reason && <small> {promotion.cancel_reason}</small>}
          </>
        )
      },
    },
  ]
  if (canEdit) {
    promotionColumns.push({
      id: 'action',
      header: '',
      cell: (promotion) => {
        const cancellable = !promotion.cancelled_at && promotion.first_week > currentWeek
        return (
          <>
            {cancellable && cancelling !== promotion.id && (
              <button
                type="button"
                className="secondary row-action"
                onClick={() => {
                  setCancelling(promotion.id)
                  setReason('')
                }}
              >
                Annuler
              </button>
            )}
            {cancelling === promotion.id && (
              <span className="inline-form">
                <input
                  type="text"
                  aria-label="Motif de l'annulation"
                  placeholder="Motif"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
                <button type="button" className="danger" onClick={() => void cancel(promotion)}>
                  Confirmer
                </button>
                <button type="button" className="secondary" onClick={() => setCancelling(null)}>
                  Retour
                </button>
              </span>
            )}
          </>
        )
      },
    })
  }

  return (
    <>
      <h2>Promotions</h2>
      <p className="hint">
        Annoncées par les enseignes 6 à 8 semaines avant, jusqu'à ×3 en volume. Une annonce plus
        tardive est acceptée mais signalée.
      </p>
      <ErrorList messages={errors} />
      {promotions.data && (
        <DataTable
          caption="Promotions"
          rows={promotions.data.results}
          columns={promotionColumns}
          rowKey={(promotion) => promotion.id}
          empty="Aucune promotion."
        />
      )}
      {canEdit && (
        <PromotionForm
          defaultCustomer={customer}
          customers={customers}
          rows={rows}
          weeks={weeks}
          onDone={onChange}
        />
      )}
    </>
  )
}

function PromotionForm(props: {
  defaultCustomer: string
  customers: Customer[]
  rows: ForecastRow[]
  weeks: ForecastWeek[]
  onDone: () => void
}) {
  const { defaultCustomer, customers, rows, weeks, onDone } = props
  const [customer, setCustomer] = useState(defaultCustomer)
  const [article, setArticle] = useState('')
  const [firstWeek, setFirstWeek] = useState('')
  const [lastWeek, setLastWeek] = useState('')
  const [coefficient, setCoefficient] = useState('2')
  const [announcedOn, setAnnouncedOn] = useState(todayIso())
  const [comment, setComment] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  const products = rows.filter((row) => String(row.customer) === customer)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setErrors([])
    setMessage('')
    try {
      const created = await apiPost<Promotion>('/api/previsions/promotions/', {
        customer: Number(customer),
        article: Number(article),
        first_week: firstWeek,
        last_week: lastWeek || firstWeek,
        coefficient,
        announced_on: announcedOn,
        comment,
      })
      setMessage(
        created.late_notice
          ? `Promotion enregistrée. Attention : annoncée ${created.notice_days} jours avant, moins des 6 semaines habituelles.`
          : 'Promotion enregistrée.',
      )
      setArticle('')
      setComment('')
      onDone()
    } catch (error) {
      setErrors(errorMessages(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="panel form" onSubmit={submit} aria-label="Nouvelle promotion">
      <h3>Nouvelle promotion</h3>
      <ErrorList messages={errors} />
      {message && <p className="status status-ok">{message}</p>}
      <div className="form-grid">
        <label>
          Enseigne
          <select
            value={customer}
            onChange={(e) => {
              setCustomer(e.target.value)
              setArticle('')
            }}
            required
          >
            <option value="">Choisir…</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} – {c.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Produit
          <select value={article} onChange={(e) => setArticle(e.target.value)} required>
            <option value="">Choisir…</option>
            {products.map((row) => (
              <option key={row.article} value={row.article}>
                {row.article_code} – {row.article_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Première semaine
          <select value={firstWeek} onChange={(e) => setFirstWeek(e.target.value)} required>
            <option value="">Choisir…</option>
            {weeks.map((w) => (
              <option key={w.week} value={w.week}>
                {w.label} (du {formatDate(w.week)})
              </option>
            ))}
          </select>
        </label>
        <label>
          Dernière semaine
          <select value={lastWeek} onChange={(e) => setLastWeek(e.target.value)}>
            <option value="">Même semaine</option>
            {weeks
              .filter((w) => !firstWeek || w.week >= firstWeek)
              .map((w) => (
                <option key={w.week} value={w.week}>
                  {w.label} (du {formatDate(w.week)})
                </option>
              ))}
          </select>
        </label>
        <label>
          Coefficient (×)
          <input
            type="number"
            min="1.01"
            max="3"
            step="0.01"
            className="qty"
            value={coefficient}
            onChange={(e) => setCoefficient(e.target.value)}
            required
          />
        </label>
        <label>
          Annoncée le
          <input type="date" value={announcedOn} max={todayIso()} onChange={(e) => setAnnouncedOn(e.target.value)} />
        </label>
        <label>
          Commentaire
          <input type="text" value={comment} onChange={(e) => setComment(e.target.value)} />
        </label>
      </div>
      <div className="form-actions">
        <button type="submit" disabled={saving}>
          Enregistrer la promotion
        </button>
      </div>
    </form>
  )
}

// --- Fiabilité à S-1 ------------------------------------------------------------------

function AccuracySection({ customer, version }: { customer: string; version: number }) {
  const { data, error } = useApi<Accuracy>(`/api/previsions/accuracy/?customer=${customer}&v=${version}`)
  const target = Number(data?.target ?? 80)
  return (
    <>
      <h2>Fiabilité des prévisions à S-1</h2>
      <p className="hint">
        Pour chaque semaine : la dernière version figée avant son lundi, comparée aux quantités
        commandées. Fiabilité = 1 − écart absolu ÷ commandes réelles, produit par produit et enseigne
        par enseigne. Objectif : ≥ {formatDecimal(data?.target ?? '80')} %. La semaine en cours n'est
        pas comptée.
      </p>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          {data.accuracy !== null && (
            <div className="stat-strip" aria-label="Fiabilité globale">
              <div className={Number(data.accuracy) >= target ? 'stat' : 'stat stat-danger'}>
                <strong>{formatDecimal(data.accuracy)} %</strong>
                <span>fiabilité des semaines terminées (objectif ≥ {formatDecimal(data.target)} %)</span>
              </div>
            </div>
          )}
          <DataTable
            caption="Fiabilité des prévisions à S-1"
            rows={data.weeks}
            rowKey={(week) => week.week}
            empty="Aucune semaine avec une prévision figée la semaine précédente."
            columns={[
              {
                id: 'week',
                header: 'Semaine',
                sortValue: (week) => week.week,
                cell: (week) => (
                  <>
                    {week.label} <small>du {formatDate(week.week)}</small>
                  </>
                ),
              },
              {
                id: 'version',
                header: 'Version S-1',
                sortValue: (week) => week.version_number,
                cell: (week) => (
                  <>
                    {week.version_number} <small>{formatDateTime(week.version_created_at)}</small>
                  </>
                ),
              },
              {
                id: 'forecast',
                header: 'Prévu',
                numeric: true,
                sortValue: (week) => Number(week.forecast),
                cell: (week) => formatDecimal(week.forecast),
              },
              {
                id: 'actual',
                header: 'Commandé',
                numeric: true,
                sortValue: (week) => Number(week.actual),
                cell: (week) => formatDecimal(week.actual),
              },
              {
                id: 'error',
                header: 'Écart absolu',
                numeric: true,
                sortValue: (week) => Number(week.abs_error),
                cell: (week) => formatDecimal(week.abs_error),
              },
              {
                id: 'accuracy',
                header: 'Fiabilité',
                numeric: true,
                sortValue: (week) => (week.accuracy === null ? null : Number(week.accuracy)),
                cell: (week) =>
                  !week.complete ? (
                    <span className="badge badge-neutral">en cours</span>
                  ) : week.accuracy === null ? (
                    '—'
                  ) : (
                    <span className={`badge ${Number(week.accuracy) >= target ? 'badge-ok' : 'badge-danger'}`}>
                      {formatDecimal(week.accuracy)} %
                    </span>
                  ),
              },
            ]}
          />
        </>
      )}
    </>
  )
}

// --- Versions figées ------------------------------------------------------------------

function VersionsSection({ version }: { version: number }) {
  const { data } = useApi<Paginated<ForecastVersion>>(`/api/previsions/versions/?v=${version}`)
  return (
    <>
      <h2>Versions figées</h2>
      {data && (
        <DataTable
          caption="Versions figées"
          rows={data.results}
          rowKey={(item) => item.id}
          empty="Aucune version figée."
          columns={[
            { id: 'number', header: 'Numéro', sortValue: (item) => item.number, cell: (item) => item.number },
            {
              id: 'created',
              header: 'Figée le',
              sortValue: (item) => item.created_at,
              cell: (item) => (
                <>
                  {formatDateTime(item.created_at)}
                  {item.created_by_name && <small> · {item.created_by_name}</small>}
                </>
              ),
            },
            { id: 'source', header: 'Origine', sortValue: (item) => item.source_label, cell: (item) => item.source_label },
            {
              id: 'weeks',
              header: 'Semaines',
              sortValue: (item) => item.first_week_label,
              cell: (item) => `à partir de ${item.first_week_label}`,
            },
            {
              id: 'lines',
              header: 'Lignes',
              numeric: true,
              sortValue: (item) => item.line_count,
              cell: (item) => item.line_count,
            },
            {
              id: 'total',
              header: 'Quantité totale',
              numeric: true,
              sortValue: (item) => Number(item.total_quantity),
              cell: (item) => formatDecimal(item.total_quantity),
            },
            { id: 'comment', header: 'Commentaire', cell: (item) => item.comment },
          ]}
        />
      )}
    </>
  )
}
