import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { ProductionOrderDetail, ProposalRow } from '../api/production'
import { ErrorList } from '../components/ErrorList'
import { formatDate, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

type Key = string // composant + lot + emplacement

const keyOf = (component: number, lot: number, location: number): Key =>
  `${component}-${lot}-${location}`

/** Déclaration de production : lots pré-remplis dans l'ordre FEFO (règle 4). */
export function DeclarationPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const order = useApi<ProductionOrderDetail>(`/api/production/orders/${id}/`)
  const [quantity, setQuantity] = useState('')
  const [proposalFor, setProposalFor] = useState<string | null>(null)
  const proposal = useApi<ProposalRow[]>(
    proposalFor ? `/api/production/orders/${id}/proposal/?quantity=${proposalFor}` : null,
  )
  // Quantités saisies (sinon la valeur proposée) et justifications hors FEFO
  const [taken, setTaken] = useState<Record<Key, string>>({})
  const [justifications, setJustifications] = useState<Record<Key, string>>({})
  const [comment, setComment] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [saving, setSaving] = useState(false)

  if (order.error) return <p className="error">{order.error}</p>
  if (!order.data) return <p>Chargement…</p>
  const o = order.data

  const valueOf = (row: ProposalRow, lotIndex: number) => {
    const lot = row.lots[lotIndex]
    const key = keyOf(row.component, lot.lot, lot.location)
    return taken[key] ?? String(Number(lot.suggested))
  }

  /** Un lot est hors FEFO s'il est utilisé alors qu'un lot qui périme avant n'est pas épuisé. */
  const isOffFefo = (row: ProposalRow, lotIndex: number) => {
    if (Number(valueOf(row, lotIndex)) <= 0) return false
    return row.lots.slice(0, lotIndex).some((earlier, index) => {
      return Number(valueOf(row, index)) < Number(earlier.available)
    })
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!proposal.data) return
    setSaving(true)
    setErrors([])
    const consumptions = proposal.data.flatMap((row) =>
      row.lots
        .map((lot, index) => ({ lot, index }))
        .filter(({ index }) => Number(valueOf(row, index)) > 0)
        .map(({ lot, index }) => ({
          lot: lot.lot,
          location: lot.location,
          quantity: valueOf(row, index),
          justification: justifications[keyOf(row.component, lot.lot, lot.location)] ?? '',
        })),
    )
    try {
      await apiPost(`/api/production/orders/${id}/declare/`, {
        quantity: proposalFor,
        comment,
        consumptions,
      })
      navigate(`/production/${id}`)
    } catch (error) {
      setErrors(errorMessages(error))
      setSaving(false)
    }
  }

  return (
    <section>
      <p>
        <Link to={`/production/${id}`}>← Retour à l'OF</Link>
      </p>
      <h1>
        Déclarer une production <small>{o.number} – {o.article_code}</small>
      </h1>

      <form
        className="filters"
        onSubmit={(e) => {
          e.preventDefault()
          setTaken({})
          setJustifications({})
          setProposalFor(quantity)
        }}
      >
        <label className="stacked">
          Quantité produite ({o.unit})
          <input
            type="number"
            min="0"
            step="any"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            required
          />
        </label>
        <button type="submit">Proposer les lots (FEFO)</button>
      </form>

      {proposal.error && <p className="error">{proposal.error}</p>}
      {proposal.data && (
        <form className="form" onSubmit={handleSubmit}>
          <p className="hint">
            Les quantités sont pré-remplies avec les lots qui périment le premier. Corrige-les avec
            ce qui a réellement été consommé. Utiliser un autre lot demande une justification.
          </p>
          {proposal.data.map((row) => (
            <fieldset key={row.component} className="panel">
              <legend>
                {row.component_code} – {row.component_name}{' '}
                <small>
                  (besoin théorique : {formatDecimal(row.need)} {row.unit})
                </small>
              </legend>
              {Number(row.missing) > 0 && (
                <p className="error">
                  Stock libéré insuffisant à l'usine : il manque {formatDecimal(row.missing)}{' '}
                  {row.unit}.
                </p>
              )}
              {row.lots.length > 0 && (
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Lot</th>
                        <th>Péremption</th>
                        <th>Emplacement</th>
                        <th className="num">Disponible</th>
                        <th className="num">Consommé</th>
                        <th>Justification (si hors FEFO)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {row.lots.map((lot, index) => {
                        const key = keyOf(row.component, lot.lot, lot.location)
                        const offFefo = isOffFefo(row, index)
                        return (
                          <tr key={key}>
                            <td>{lot.lot_number}</td>
                            <td>{formatDate(lot.expiry_date)}</td>
                            <td>{lot.location_code}</td>
                            <td className="num">
                              {formatDecimal(lot.available)} {row.unit}
                            </td>
                            <td className="num">
                              <input
                                type="number"
                                min="0"
                                step="any"
                                className="qty"
                                aria-label={`Consommé ${lot.lot_number}`}
                                value={valueOf(row, index)}
                                onChange={(e) => setTaken({ ...taken, [key]: e.target.value })}
                              />
                            </td>
                            <td>
                              {offFefo && (
                                <input
                                  aria-label={`Justification ${lot.lot_number}`}
                                  placeholder="Obligatoire : lot hors FEFO"
                                  value={justifications[key] ?? ''}
                                  onChange={(e) =>
                                    setJustifications({ ...justifications, [key]: e.target.value })
                                  }
                                />
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </fieldset>
          ))}
          <label className="stacked">
            Commentaire
            <input value={comment} onChange={(e) => setComment(e.target.value)} />
          </label>
          <ErrorList messages={errors} />
          <div className="form-actions">
            <button type="submit" disabled={saving}>
              Enregistrer la déclaration ({formatDecimal(proposalFor)} {o.unit})
            </button>
          </div>
        </form>
      )}
    </section>
  )
}
