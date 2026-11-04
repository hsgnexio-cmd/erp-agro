import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { Location, Paginated, PurchaseOrder, PurchaseOrderLine, Reception } from '../api/types'
import { ErrorList } from '../components/ErrorList'
import { ReceptionResult } from '../components/ReceptionResult'
import { formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

interface LineInput {
  quantity: string
  supplierLotNumber: string
  expiryDate: string
  temperature: string
  appearanceOk: boolean
}

const remaining = (line: PurchaseOrderLine) =>
  Math.max(Number(line.quantity) - Number(line.received_quantity), 0)

const needsTemperature = (line: PurchaseOrderLine) =>
  ['froid_positif', 'froid_negatif'].includes(line.article_temperature_class)

const needsDate = (line: PurchaseOrderLine) => ['DLC', 'DDM'].includes(line.article_date_type)

export function ReceptionFormPage() {
  const { id } = useParams()
  const order = useApi<PurchaseOrder>(`/api/achats/orders/${id}/`)
  const locations = useApi<Paginated<Location>>(
    order.data ? `/api/referentiel/locations/?site=${order.data.delivery_site}&active=true` : null,
  )

  const [deliveryNote, setDeliveryNote] = useState('')
  const [documentsOk, setDocumentsOk] = useState(true)
  const [locationId, setLocationId] = useState('')
  const [inputs, setInputs] = useState<Record<number, Partial<LineInput>>>({})
  const [errors, setErrors] = useState<string[]>([])
  const [result, setResult] = useState<Reception | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (order.error) return <p className="error">{order.error}</p>
  if (!order.data) return <p>Chargement…</p>

  const openLines = order.data.lines.filter((line) => remaining(line) > 0)
  // Par défaut, zone de quarantaine à la température de conservation des produits
  const temperatureClass = openLines[0]?.article_temperature_class
  const defaultLocation = locations.data?.results.find(
    (l) => l.code.includes('-QUAR') && l.temperature_class === temperatureClass,
  )
  const location = locationId || (defaultLocation ? String(defaultLocation.id) : '')

  // Valeur saisie, ou valeur par défaut (quantité restant à recevoir, aspect conforme)
  const value = (line: PurchaseOrderLine): LineInput => ({
    quantity: String(remaining(line)),
    supplierLotNumber: '',
    expiryDate: '',
    temperature: '',
    appearanceOk: true,
    ...inputs[line.id],
  })
  const update = (lineId: number, change: Partial<LineInput>) =>
    setInputs({ ...inputs, [lineId]: { ...inputs[lineId], ...change } })

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setErrors([])
    const lines = openLines
      .map((line) => ({ line, input: value(line) }))
      .filter(({ input }) => Number(input.quantity) > 0)
      .map(({ line, input }) => ({
        order_line: line.id,
        quantity: input.quantity,
        supplier_lot_number: input.supplierLotNumber,
        expiry_date: input.expiryDate || null,
        temperature: input.temperature === '' ? null : input.temperature,
        appearance_ok: input.appearanceOk,
      }))
    try {
      setResult(
        await apiPost<Reception>('/api/achats/receptions/', {
          order: order.data!.id,
          location: Number(location),
          delivery_note_number: deliveryNote,
          documents_ok: documentsOk,
          lines,
        }),
      )
    } catch (error) {
      setErrors(errorMessages(error))
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    return (
      <section>
        <h1>Réception enregistrée</h1>
        <ReceptionResult reception={result} />
        <p>
          Les lots conformes sont en <strong>quarantaine</strong> jusqu'au contrôle qualité. Les
          lots non conformes sont <strong>bloqués</strong>.
        </p>
        <Link to={`/commandes/${order.data.id}`} className="button">
          Retour à la commande
        </Link>
      </section>
    )
  }

  return (
    <section>
      <p>
        <Link to={`/commandes/${order.data.id}`}>← Retour à la commande</Link>
      </p>
      <h1>
        Réception {order.data.number} <small>{order.data.supplier_name}</small>
      </h1>
      <form className="form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label>
            N° de bon de livraison
            <input value={deliveryNote} onChange={(e) => setDeliveryNote(e.target.value)} required />
          </label>
          <label>
            Emplacement de dépôt
            <select value={location} onChange={(e) => setLocationId(e.target.value)} required>
              {locations.data?.results.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.code} – {l.name}
                </option>
              ))}
            </select>
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={documentsOk}
              onChange={(e) => setDocumentsOk(e.target.checked)}
            />
            Documents de livraison présents et conformes
          </label>
        </div>

        <h2>Lignes à recevoir</h2>
        <p className="hint">
          Mets la quantité à 0 pour une ligne non livrée. La température est obligatoire pour le
          frais et le surgelé.
        </p>
        {openLines.map((line) => {
          const input = value(line)
          return (
            <fieldset key={line.id} className="reception-line">
              <legend>
                {line.article_code} – {line.article_name}{' '}
                <small>
                  (reste à recevoir : {formatDecimal(String(remaining(line)))} {line.unit})
                </small>
              </legend>
              <label>
                Quantité ({line.unit})
                <input
                  type="number"
                  min="0"
                  step="any"
                  value={input.quantity}
                  onChange={(e) => update(line.id, { quantity: e.target.value })}
                />
              </label>
              <label>
                Lot fournisseur
                <input
                  value={input.supplierLotNumber}
                  onChange={(e) => update(line.id, { supplierLotNumber: e.target.value })}
                />
              </label>
              {needsDate(line) && (
                <label>
                  {line.article_date_type}
                  <input
                    type="date"
                    value={input.expiryDate}
                    onChange={(e) => update(line.id, { expiryDate: e.target.value })}
                  />
                </label>
              )}
              {needsTemperature(line) && (
                <label>
                  Température (°C)
                  <input
                    type="number"
                    step="0.1"
                    value={input.temperature}
                    onChange={(e) => update(line.id, { temperature: e.target.value })}
                  />
                </label>
              )}
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={input.appearanceOk}
                  onChange={(e) => update(line.id, { appearanceOk: e.target.checked })}
                />
                Aspect conforme
              </label>
            </fieldset>
          )
        })}

        <ErrorList messages={errors} />
        <div className="form-actions">
          <button type="submit" disabled={submitting || openLines.length === 0}>
            Enregistrer la réception
          </button>
        </div>
      </form>
    </section>
  )
}
