import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { CustomerOrderDetail, PickingLine, PickingProposal, ShipmentDetail } from '../api/sales'
import { ErrorList } from '../components/ErrorList'
import { formatDate, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

type Key = string // ligne de commande + lot + emplacement

const keyOf = (orderLine: number, lot: number, location: number): Key =>
  `${orderLine}-${lot}-${location}`

/** Préparation d'une commande client : lots pré-remplis dans l'ordre FEFO (règle 4). */
export function PreparationPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const order = useApi<CustomerOrderDetail>(`/api/ventes/orders/${id}/`)
  const proposal = useApi<PickingProposal>(`/api/ventes/orders/${id}/picking-proposal/`)
  // Quantités saisies (sinon la valeur proposée) et justifications hors FEFO
  const [taken, setTaken] = useState<Record<Key, string>>({})
  const [justifications, setJustifications] = useState<Record<Key, string>>({})
  const [errors, setErrors] = useState<string[]>([])
  const [saving, setSaving] = useState(false)

  if (order.error) return <p className="error">{order.error}</p>
  if (proposal.error) return <p className="error">{proposal.error}</p>
  if (!order.data || !proposal.data) return <p>Chargement…</p>
  const o = order.data
  const p = proposal.data

  const valueOf = (row: PickingLine, lotIndex: number) => {
    const lot = row.lots[lotIndex]
    return taken[keyOf(row.order_line, lot.lot, lot.location)] ?? String(Number(lot.suggested))
  }

  const preparedOf = (row: PickingLine) =>
    row.lots.reduce((total, _lot, index) => total + (Number(valueOf(row, index)) || 0), 0)

  /** Un lot est hors FEFO s'il est pris alors qu'un lot qui périme avant n'est pas épuisé. */
  const isOffFefo = (row: PickingLine, lotIndex: number) => {
    if (Number(valueOf(row, lotIndex)) <= 0) return false
    return row.lots
      .slice(0, lotIndex)
      .some((earlier, index) => Number(valueOf(row, index)) < Number(earlier.available))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setErrors([])
    const lines = p.lines.flatMap((row) =>
      row.lots
        .map((lot, index) => ({ lot, index }))
        .filter(({ index }) => Number(valueOf(row, index)) > 0)
        .map(({ lot, index }) => ({
          order_line: row.order_line,
          lot: lot.lot,
          location: lot.location,
          quantity: valueOf(row, index),
          justification: justifications[keyOf(row.order_line, lot.lot, lot.location)] ?? '',
        })),
    )
    try {
      const shipment = await apiPost<ShipmentDetail>(`/api/ventes/orders/${id}/prepare/`, { lines })
      navigate(`/expeditions/${shipment.id}`)
    } catch (error) {
      setErrors(errorMessages(error))
      setSaving(false)
    }
  }

  return (
    <section>
      <p>
        <Link to={`/ventes/${id}`}>← Retour à la commande</Link>
      </p>
      <h1>
        Préparer la commande <small>{o.number} – {o.customer_code}</small>
      </h1>
      <p className="hint">
        Livraison demandée le {formatDate(p.requested_delivery_date)} à {o.warehouse_name}.{' '}
        {o.customer_code} exige au moins {formatDecimal(p.min_remaining_shelf_life_pct)} % de durée
        de vie restante à la livraison : les lots trop courts ne sont pas proposés. Les quantités
        sont pré-remplies avec les lots qui périment le premier ; prendre un autre lot demande une
        justification. Ce qui manque sera une rupture : il n'y a pas de reliquat.
      </p>

      <form className="form" onSubmit={handleSubmit}>
        {p.lines.map((row) => {
          const prepared = preparedOf(row)
          const missing = Number(row.ordered) - prepared
          return (
            <fieldset key={row.order_line} className="panel">
              <legend>
                {row.article_code} – {row.article_name}{' '}
                <small>
                  (commandé : {formatDecimal(row.ordered)} {row.unit}
                  {row.min_expiry_date && `, DLC au moins le ${formatDate(row.min_expiry_date)}`})
                </small>
              </legend>
              {row.lots.length === 0 ? (
                <p className="error">
                  Aucun lot libéré assez long à la plateforme : rupture sur ce produit.
                </p>
              ) : (
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Lot</th>
                        <th>DLC</th>
                        <th>Emplacement</th>
                        <th className="num">Disponible</th>
                        <th className="num">Préparé</th>
                        <th>Justification (si hors FEFO)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {row.lots.map((lot, index) => {
                        const key = keyOf(row.order_line, lot.lot, lot.location)
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
                                aria-label={`Préparé ${lot.lot_number}`}
                                value={valueOf(row, index)}
                                onChange={(e) => setTaken({ ...taken, [key]: e.target.value })}
                              />
                            </td>
                            <td>
                              {isOffFefo(row, index) && (
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
              {missing > 0 && row.lots.length > 0 && (
                <p className="error">
                  Rupture : {formatDecimal(String(missing))} {row.unit} ne seront pas livrés.
                </p>
              )}
              {missing < 0 && (
                <p className="error">
                  Plus que la quantité commandée : on ne livre jamais de surplus.
                </p>
              )}
              {row.too_short.length > 0 && (
                <p className="hint">
                  Lots écartés car trop courts pour {o.customer_code} :{' '}
                  {row.too_short
                    .map(
                      (lot) =>
                        `${lot.lot_number} (DLC ${formatDate(lot.expiry_date)}, ${formatDecimal(lot.available)} ${row.unit})`,
                    )
                    .join(', ')}
                  .
                </p>
              )}
            </fieldset>
          )
        })}
        <ErrorList messages={errors} />
        <div className="form-actions">
          <button type="submit" disabled={saving}>
            Enregistrer la préparation
          </button>
        </div>
      </form>
    </section>
  )
}
