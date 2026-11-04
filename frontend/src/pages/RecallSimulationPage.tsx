import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { RecallDetail, RecallImpact } from '../api/quality'
import { useAuth } from '../auth/context'
import { QUALITY_ROLES, hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { RecallImpactView } from '../components/RecallImpactView'
import { useApi } from '../hooks/useApi'

/** Simulation d'un rappel (sans rien modifier), puis lancement officiel par la qualité. */
export function RecallSimulationPage() {
  const [searchParams] = useSearchParams()
  const lot = searchParams.get('lot') ?? ''
  const { user } = useAuth()
  const navigate = useNavigate()
  const impact = useApi<RecallImpact>(
    lot ? `/api/qualite/recall-simulation/?lot=${encodeURIComponent(lot)}` : null,
  )
  const [reason, setReason] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [launching, setLaunching] = useState(false)

  async function handleLaunch(event: FormEvent) {
    event.preventDefault()
    if (!window.confirm('Lancer le rappel ? Tous les lots concernés avec du stock seront bloqués.')) {
      return
    }
    setLaunching(true)
    setErrors([])
    try {
      const recall = await apiPost<RecallDetail>('/api/qualite/recalls/', {
        lot_number: lot,
        reason,
      })
      navigate(`/rappels/${recall.id}`)
    } catch (error) {
      setErrors(errorMessages(error))
      setLaunching(false)
    }
  }

  return (
    <section>
      <p>
        <Link to={`/tracabilite?lot=${encodeURIComponent(lot)}`}>← Retour à la traçabilité</Link>
      </p>
      <h1>
        Simulation de rappel <small>lot {lot}</small>
      </h1>
      <p className="hint">Simulation : rien n'est modifié tant que le rappel n'est pas lancé.</p>
      {impact.loading && <p>Calcul en cours…</p>}
      {impact.error && <p className="error">{impact.error}</p>}
      {impact.data && (
        <>
          <RecallImpactView impact={impact.data} />
          {hasRole(user, QUALITY_ROLES) && (
            <form className="panel danger-zone" onSubmit={handleLaunch}>
              <h2>Lancer le rappel</h2>
              <p>
                Les {impact.data.lots_to_block.length} lot(s) concernés qui ont encore du stock
                seront <strong>bloqués immédiatement</strong>.
              </p>
              <label className="stacked">
                Motif du rappel (obligatoire)
                <textarea
                  rows={2}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Ex. Listeria signalée par le fournisseur sur ce lot"
                  required
                />
              </label>
              <ErrorList messages={errors} />
              <div className="form-actions">
                <button type="submit" className="danger" disabled={launching}>
                  Lancer le rappel
                </button>
              </div>
            </form>
          )}
        </>
      )}
    </section>
  )
}
