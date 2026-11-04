import { useState } from 'react'
import type { Lot, Paginated } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

const STATUSES = [
  { value: '', label: 'Tous les statuts' },
  { value: 'quarantaine', label: 'Quarantaine' },
  { value: 'libere', label: 'Libéré' },
  { value: 'bloque', label: 'Bloqué' },
  { value: 'detruit', label: 'Détruit' },
]

export function LotsPage() {
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (search) params.set('search', search)
  const { data, error } = useApi<Paginated<Lot>>(`/api/stocks/lots/?${params}`)

  return (
    <section>
      <h1>Lots</h1>
      <div className="filters">
        <input
          type="search"
          placeholder="Rechercher un lot, un lot fournisseur ou un article"
          aria-label="Rechercher"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select aria-label="Statut" value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <p className="count">{data.count} lot(s)</p>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Lot</th>
                  <th>Article</th>
                  <th>Lot fournisseur</th>
                  <th>Reçu le</th>
                  <th>DLC / DDM</th>
                  <th className="num">Quantité</th>
                  <th>Emplacement</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((lot) => (
                  <tr key={lot.id}>
                    <td>{lot.number}</td>
                    <td>
                      {lot.article_code}
                      <br />
                      <small>{lot.article_name}</small>
                    </td>
                    <td>{lot.supplier_lot_number || '—'}</td>
                    <td>{formatDate(lot.reception_date)}</td>
                    <td>
                      {lot.expiry_date ? `${formatDate(lot.expiry_date)} (${lot.date_type})` : '—'}
                    </td>
                    <td className="num">
                      {formatDecimal(lot.quantity)} {lot.unit}
                    </td>
                    <td>{lot.location_code}</td>
                    <td className="wrap">
                      <StatusBadge status={lot.status} label={lot.status_label} />
                      {lot.block_reason && <small className="reason">{lot.block_reason}</small>}
                    </td>
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
