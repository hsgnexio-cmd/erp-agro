import { ShieldAlert } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router'
import type { TraceNode, Traceability } from '../api/quality'
import { StatusBadge } from '../components/StatusBadge'
import { TraceTree } from '../components/TraceTree'
import { useApi } from '../hooks/useApi'

/** Tous les lots d'un arbre de traçabilité, sans le lot de départ. */
function descendants(node: TraceNode): TraceNode[] {
  return node.children.flatMap((child) => [child, ...descendants(child)])
}

/** Synthèse de l'arbre renvoyé par l'API : nombre de lots en amont, en aval, enseignes livrées. */
function TraceSummary({ trace }: { trace: Traceability }) {
  const upstream = descendants(trace.upstream)
  const downstream = descendants(trace.downstream)
  const shipped = [trace.downstream, ...downstream].flatMap((node) => node.shipments)
  const customers = new Set(shipped.map((shipment) => shipment.customer_code))
  const origin = trace.upstream
  return (
    <div className="stat-strip" aria-label="Synthèse de la traçabilité">
      <div className="stat">
        <strong className="lot-number">{origin.lot_number}</strong>
        <span>
          {origin.article_code} <StatusBadge status={origin.status} label={origin.status_label} />
        </span>
      </div>
      <div className="stat">
        <strong>{upstream.length}</strong>
        <span>lot(s) en amont</span>
      </div>
      <div className="stat">
        <strong>{downstream.length}</strong>
        <span>lot(s) fabriqué(s) avec ce lot</span>
      </div>
      <div className={customers.size > 0 ? 'stat stat-danger' : 'stat'}>
        <strong>{customers.size}</strong>
        <span>enseigne(s) livrée(s)</span>
      </div>
    </div>
  )
}

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
      <p className="page-intro">
        Saisis un numéro de lot pour voir de quoi il est fait (amont) et où il est allé (aval), jusqu'aux
        entrepôts des enseignes.
      </p>
      <form className="filters search-hero" onSubmit={handleSubmit}>
        <input
          aria-label="Numéro de lot"
          placeholder="Numéro de lot, ex. LR-261025-0001"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          required
        />
        <button type="submit">Tracer</button>
      </form>

      {!lot && (
        <div className="empty-state">
          <strong>Aucun lot tracé pour l'instant</strong>
          <span>
            Le numéro d'un lot se trouve dans le menu Lots, sur une réception ou sur un ordre de fabrication.
          </span>
        </div>
      )}
      {trace.loading && <p>Recherche…</p>}
      {trace.error && <p className="error">{trace.error}</p>}
      {trace.data && (
        <>
          <TraceSummary trace={trace.data} />
          <div className="actions">
            <Link
              className="button danger"
              to={`/rappels/simulation?lot=${encodeURIComponent(trace.data.upstream.lot_number)}`}
            >
              <ShieldAlert size={15} aria-hidden="true" /> Simuler un rappel de ce lot
            </Link>
          </div>
          <div className="trace-columns">
            <div className="panel">
              <h2>
                <span className="direction up" aria-hidden="true" />
                Amont : de quoi est fait ce lot ?
              </h2>
              {trace.data.upstream.children.length === 0 ? (
                <p className="hint">Lot reçu d'un fournisseur : rien en amont dans l'ERP.</p>
              ) : (
                <TraceTree node={trace.data.upstream} direction="amont" />
              )}
            </div>
            <div className="panel">
              <h2>
                <span className="direction down" aria-hidden="true" />
                Aval : où est allé ce lot ?
              </h2>
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
