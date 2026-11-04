import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { Inventory, InventoryDetail } from '../api/monitoring'
import type { Location, Paginated, Site } from '../api/types'
import { useAuth } from '../auth/context'
import { WAREHOUSE_ROLES, hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { formatDateTime } from '../format'
import { useApi } from '../hooks/useApi'

const STATUS_TONES: Record<string, string> = { en_cours: 'warn', valide: 'ok', annule: 'off' }

export function InventoriesPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const inventories = useApi<Paginated<Inventory>>('/api/stocks/inventories/')
  const sites = useApi<Paginated<Site>>('/api/referentiel/sites/?active=true')
  const [site, setSite] = useState('')
  const locations = useApi<Paginated<Location>>(
    site ? `/api/referentiel/locations/?site=${site}&active=true` : null,
  )
  const [location, setLocation] = useState('')
  const [comment, setComment] = useState('')
  const [errors, setErrors] = useState<string[]>([])

  async function handleOpen(event: FormEvent) {
    event.preventDefault()
    setErrors([])
    try {
      const created = await apiPost<InventoryDetail>('/api/stocks/inventories/', {
        site: Number(site),
        location: location ? Number(location) : null,
        comment,
      })
      navigate(`/inventaires/${created.id}`)
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  return (
    <section>
      <h1>Inventaires</h1>

      {hasRole(user, WAREHOUSE_ROLES) && (
        <form className="panel" onSubmit={handleOpen}>
          <h2>Ouvrir un inventaire</h2>
          <p className="hint">
            Les emplacements comptés sont gelés jusqu'à la validation : aucun mouvement possible.
          </p>
          <div className="form-grid">
            <label className="stacked">
              Site
              <select
                value={site}
                onChange={(e) => {
                  setSite(e.target.value)
                  setLocation('')
                }}
                required
              >
                <option value="">— Choisir —</option>
                {sites.data?.results.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.code} – {s.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked">
              Emplacement
              <select value={location} onChange={(e) => setLocation(e.target.value)}>
                <option value="">Tout le site</option>
                {locations.data?.results.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.code} – {l.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked">
              Commentaire
              <input value={comment} onChange={(e) => setComment(e.target.value)} />
            </label>
          </div>
          <ErrorList messages={errors} />
          <div className="form-actions">
            <button type="submit">Ouvrir l'inventaire</button>
          </div>
        </form>
      )}

      {inventories.data && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Numéro</th>
                <th>Périmètre</th>
                <th>Statut</th>
                <th className="num">Lignes</th>
                <th>Ouvert le</th>
                <th>Clos le</th>
              </tr>
            </thead>
            <tbody>
              {inventories.data.results.length === 0 && (
                <tr>
                  <td colSpan={6}>Aucun inventaire.</td>
                </tr>
              )}
              {inventories.data.results.map((inv) => (
                <tr key={inv.id}>
                  <td>
                    <Link to={`/inventaires/${inv.id}`}>{inv.number}</Link>
                  </td>
                  <td>{inv.location_code ?? `Site ${inv.site_code}`}</td>
                  <td>
                    <span className={`badge badge-${STATUS_TONES[inv.status]}`}>
                      {inv.status_label}
                    </span>
                  </td>
                  <td className="num">{inv.line_count}</td>
                  <td>{formatDateTime(inv.opened_at)}</td>
                  <td>{formatDateTime(inv.closed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
