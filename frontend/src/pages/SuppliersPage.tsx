import { useState } from 'react'
import type { Paginated, Supplier } from '../api/types'
import { formatDate } from '../format'
import { useApi } from '../hooks/useApi'

export function SuppliersPage() {
  const [search, setSearch] = useState('')
  const params = new URLSearchParams()
  if (search) params.set('search', search)
  const { data, error } = useApi<Paginated<Supplier>>(`/api/referentiel/suppliers/?${params}`)

  return (
    <section>
      <h1>Fournisseurs</h1>
      <div className="filters">
        <input
          type="search"
          placeholder="Rechercher un fournisseur"
          aria-label="Rechercher"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Raison sociale</th>
                <th>Ville</th>
                <th>Catégories</th>
                <th className="num">Délai</th>
                <th>Audit</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((s) => (
                <tr key={s.id} className={s.active ? '' : 'inactive'}>
                  <td>{s.code}</td>
                  <td>{s.name}</td>
                  <td>{s.city || '—'}</td>
                  <td>{s.category_codes.join(', ') || 'Emballages'}</td>
                  <td className="num">{s.lead_time_days} j</td>
                  <td>
                    {s.audited ? (
                      `Audité le ${formatDate(s.last_audit_date)}`
                    ) : (
                      <span className="badge badge-warn">Non audité</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
