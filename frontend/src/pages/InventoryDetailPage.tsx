import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { InventoryDetail } from '../api/monitoring'
import type { Location, Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { WAREHOUSE_ROLES, hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { formatDate, formatDateTime, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

/** Feuille de comptage (à l'aveugle), puis écarts et validation. */
export function InventoryDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const [version, setVersion] = useState(0)
  // Étape « écarts » : on affiche les quantités théoriques juste avant de valider
  const [showDifferences, setShowDifferences] = useState(false)
  const inventory = useApi<InventoryDetail>(
    `/api/stocks/inventories/${id}/?v=${version}${showDifferences ? '&show_differences=1' : ''}`,
  )
  const [counts, setCounts] = useState<Record<number, string>>({})
  const [errors, setErrors] = useState<string[]>([])
  const [message, setMessage] = useState('')
  const [found, setFound] = useState({ lot: '', location: '', quantity: '' })
  const locations = useApi<Paginated<Location>>(
    inventory.data ? `/api/referentiel/locations/?site=${inventory.data.site}&active=true` : null,
  )

  if (inventory.error) return <p className="error">{inventory.error}</p>
  if (!inventory.data) return <p>Chargement…</p>
  const inv = inventory.data
  const isOpen = inv.status === 'en_cours'
  const canCount = isOpen && hasRole(user, WAREHOUSE_ROLES)

  const counted = (lineId: number, saved: string | null) =>
    counts[lineId] ?? (saved === null ? '' : String(Number(saved)))

  async function run(path: string, body: unknown, success: string) {
    setErrors([])
    setMessage('')
    try {
      await apiPost(`/api/stocks/inventories/${id}/${path}/`, body)
      setMessage(success)
      setCounts({})
      setVersion((v) => v + 1)
      return true
    } catch (error) {
      setErrors(errorMessages(error))
      return false
    }
  }

  function saveCounts(event: FormEvent) {
    event.preventDefault()
    const lines = Object.entries(counts).map(([lineId, value]) => ({
      id: Number(lineId),
      counted_quantity: value === '' ? null : value,
    }))
    void run('count', { lines }, 'Comptage enregistré.')
  }

  function addFoundLot(event: FormEvent) {
    event.preventDefault()
    void run(
      'add-lot',
      {
        lot_number: found.lot,
        location: Number(found.location),
        counted_quantity: found.quantity,
      },
      'Lot ajouté à la feuille de comptage.',
    ).then((ok) => ok && setFound({ lot: '', location: '', quantity: '' }))
  }

  async function validate() {
    if (!window.confirm('Valider l’inventaire ? Les écarts deviendront des mouvements de stock.')) {
      return
    }
    if (await run('validate', {}, 'Inventaire validé : les écarts sont enregistrés.')) {
      setShowDifferences(false)
    }
  }

  const missing = inv.lines.filter((line) => line.counted_quantity === null).length
  const showExpected = !isOpen || showDifferences

  return (
    <section>
      <p>
        <Link to="/inventaires">← Retour aux inventaires</Link>
      </p>
      <div className="page-title">
        <h1>
          {inv.number} <small>{inv.location_code ?? `Site ${inv.site_code}`}</small>
        </h1>
        <span className={`badge badge-${isOpen ? 'warn' : inv.status === 'valide' ? 'ok' : 'off'}`}>
          {inv.status_label}
        </span>
      </div>
      <p className="hint">
        Ouvert le {formatDateTime(inv.opened_at)}
        {inv.opened_by_name && ` par ${inv.opened_by_name}`}
        {inv.closed_at && ` · clos le ${formatDateTime(inv.closed_at)}`}
        {inv.comment && ` · ${inv.comment}`}
      </p>
      {isOpen && !showDifferences && (
        <p className="hint">
          Comptage à l'aveugle : saisis ce que tu trouves physiquement. Les quantités théoriques
          s'affichent à l'étape des écarts.
        </p>
      )}

      {message && (
        <p className="status status-ok" role="status">
          {message}
        </p>
      )}
      <ErrorList messages={errors} />

      <form onSubmit={saveCounts}>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Emplacement</th>
                <th>Lot</th>
                <th>Article</th>
                <th>DLC / DDM</th>
                {showExpected && <th className="num">Théorique</th>}
                <th className="num">Compté</th>
                {showExpected && <th className="num">Écart</th>}
              </tr>
            </thead>
            <tbody>
              {inv.lines.length === 0 && (
                <tr>
                  <td colSpan={7}>Aucun stock dans ce périmètre.</td>
                </tr>
              )}
              {inv.lines.map((line) => {
                const difference = line.difference === null ? 0 : Number(line.difference)
                return (
                  <tr key={line.id}>
                    <td>{line.location_code}</td>
                    <td>
                      <Link to={`/lots/${line.lot}`}>{line.lot_number}</Link>
                      {line.added_during_count && <small> (trouvé)</small>}
                    </td>
                    <td>
                      {line.article_code}
                      <br />
                      <small>{line.article_name}</small>
                    </td>
                    <td>{formatDate(line.expiry_date)}</td>
                    {showExpected && (
                      <td className="num">
                        {formatDecimal(line.expected_quantity)} {line.unit}
                      </td>
                    )}
                    <td className="num">
                      {canCount && !showDifferences ? (
                        <>
                          <input
                            type="number"
                            min="0"
                            step="any"
                            className="qty"
                            aria-label={`Compté ${line.lot_number} ${line.location_code}`}
                            value={counted(line.id, line.counted_quantity)}
                            onChange={(e) => setCounts({ ...counts, [line.id]: e.target.value })}
                          />{' '}
                          {line.unit}
                        </>
                      ) : (
                        `${formatDecimal(line.counted_quantity)} ${line.unit}`
                      )}
                    </td>
                    {showExpected && (
                      <td className={`num ${difference < 0 ? 'negative' : ''}`}>
                        {line.difference === null
                          ? '—'
                          : `${difference > 0 ? '+' : ''}${formatDecimal(line.difference)} ${line.unit}`}
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {canCount && (
          <div className="actions">
            {!showDifferences ? (
              <>
                <button type="submit" disabled={Object.keys(counts).length === 0}>
                  Enregistrer le comptage
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={missing > 0 || Object.keys(counts).length > 0}
                  onClick={() => setShowDifferences(true)}
                >
                  Voir les écarts{missing > 0 && ` (${missing} ligne(s) à compter)`}
                </button>
              </>
            ) : (
              <>
                <button type="button" onClick={() => void validate()}>
                  Valider l'inventaire
                </button>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setShowDifferences(false)}
                >
                  Revenir au comptage
                </button>
              </>
            )}
            <button
              type="button"
              className="danger"
              onClick={() =>
                window.confirm('Annuler l’inventaire ? Aucun ajustement ne sera fait.') &&
                void run('cancel', {}, 'Inventaire annulé.')
              }
            >
              Annuler l'inventaire
            </button>
          </div>
        )}
      </form>

      {canCount && !showDifferences && (
        <form className="panel" onSubmit={addFoundLot}>
          <h2>Ajouter un lot trouvé sur place</h2>
          <div className="form-grid">
            <label className="stacked">
              Numéro de lot
              <input
                value={found.lot}
                onChange={(e) => setFound({ ...found, lot: e.target.value })}
                placeholder="LR-261025-0001"
                required
              />
            </label>
            <label className="stacked">
              Emplacement
              <select
                value={found.location}
                onChange={(e) => setFound({ ...found, location: e.target.value })}
                required
              >
                <option value="">— Choisir —</option>
                {locations.data?.results
                  .filter((l) => inv.location === null || l.id === inv.location)
                  .map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.code}
                    </option>
                  ))}
              </select>
            </label>
            <label className="stacked">
              Quantité comptée
              <input
                type="number"
                min="0"
                step="any"
                value={found.quantity}
                onChange={(e) => setFound({ ...found, quantity: e.target.value })}
                required
              />
            </label>
          </div>
          <div className="form-actions">
            <button type="submit">Ajouter</button>
          </div>
        </form>
      )}
    </section>
  )
}
