import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router'
import type { Traceability } from '../api/quality'
import { TraceTree } from '../components/TraceTree'
import { useApi } from '../hooks/useApi'

/** Traçabilité d'un lot, vers l'amont (ce qui le compose) et l'aval (où il est allé). */
export function TraceabilityPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const lot = searchParams.get('lot') ?? ''
  const [input, setInput] = useState(lot)
  const trace = useApi<Traceability>(
    lot ? `/api/qualite/traceability/?lot=${encodeURIComponent(lot)}` : null,
  )

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSearchParams({ lot: input.trim().toUpperCase() })
  }

  return (
    <section>
      <h1>Traçabilité</h1>
      <form className="filters" onSubmit={handleSubmit}>
        <input
          aria-label="Numéro de lot"
          placeholder="Numéro de lot, ex. LR-261025-0001"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          required
        />
        <button type="submit">Tracer</button>
      </form>

      {trace.loading && <p>Recherche…</p>}
      {trace.error && <p className="error">{trace.error}</p>}
      {trace.data && (
        <>
          <div className="actions">
            <Link
              className="button"
              to={`/rappels/simulation?lot=${encodeURIComponent(trace.data.upstream.lot_number)}`}
            >
              Simuler un rappel de ce lot
            </Link>
          </div>
          <div className="trace-columns">
            <div className="panel">
              <h2>⬆ Amont : de quoi est fait ce lot ?</h2>
              {trace.data.upstream.children.length === 0 ? (
                <p className="hint">Lot reçu d'un fournisseur : rien en amont dans l'ERP.</p>
              ) : (
                <TraceTree node={trace.data.upstream} direction="amont" />
              )}
            </div>
            <div className="panel">
              <h2>⬇ Aval : où est allé ce lot ?</h2>
              {trace.data.downstream.children.length === 0 &&
              trace.data.downstream.shipments.length === 0 ? (
                <p className="hint">Ce lot n'a encore été ni consommé ni expédié.</p>
              ) : (
                <TraceTree node={trace.data.downstream} direction="aval" />
              )}
            </div>
          </div>
        </>
      )}
    </section>
  )
}
