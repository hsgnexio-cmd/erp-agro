import { ExternalLink, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router'
import type { Traceability } from '../api/quality'
import type { Lot } from '../api/types'
import { formatDate, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'
import { Drawer } from './Drawer'
import { StatusBadge } from './StatusBadge'
import { TraceTree } from './TraceTree'

/** Traçabilité du lot : amont (de quoi il est fait) et aval (où il est allé, jusqu'aux clients). */
function Trace({ lotNumber }: { lotNumber: string }) {
  const trace = useApi<Traceability>(
    `/api/qualite/traceability/?lot=${encodeURIComponent(lotNumber)}`,
  )
  if (trace.loading) return <p className="hint">Recherche…</p>
  if (trace.error) return <p className="error">{trace.error}</p>
  if (!trace.data) return null
  const { upstream, downstream } = trace.data
  return (
    <div className="drawer-trace">
      <h3>
        <span className="direction up" aria-hidden="true" />
        Amont : matières et semi-finis consommés
      </h3>
      {upstream.children.length === 0 ? (
        <p className="hint">Lot reçu d'un fournisseur : rien en amont dans l'ERP.</p>
      ) : (
        <TraceTree node={upstream} direction="amont" />
      )}
      <h3>
        <span className="direction down" aria-hidden="true" />
        Aval : fabrications et expéditions
      </h3>
      {downstream.children.length === 0 && downstream.shipments.length === 0 ? (
        <p className="hint">Ce lot n'a encore été ni consommé ni expédié.</p>
      ) : (
        <TraceTree node={downstream} direction="aval" />
      )}
    </div>
  )
}

/** Fiche d'un lot dans un tiroir : l'essentiel, sa traçabilité, et l'accès au rappel. */
export function LotDrawer({ lot, onClose }: { lot: Lot | null; onClose: () => void }) {
  if (!lot) return null
  const recall = `/rappels/simulation?lot=${encodeURIComponent(lot.number)}`
  return (
    <Drawer
      open
      onClose={onClose}
      width={680}
      title={`Lot ${lot.number}`}
      subtitle={
        <>
          {lot.article_code} – {lot.article_name}{' '}
          <StatusBadge status={lot.status} label={lot.status_label} />
        </>
      }
      tabs={[
        {
          id: 'detail',
          label: 'Détail',
          content: (
            <>
              <dl className="details drawer-details">
                <dt>Article</dt>
                <dd>
                  <Link to={`/articles/${lot.article}`}>{lot.article_code}</Link> – {lot.article_name}
                </dd>
                <dt>Quantité en stock</dt>
                <dd>
                  {formatDecimal(lot.quantity)} {lot.unit}{' '}
                  <small>
                    (à l'origine : {formatDecimal(lot.initial_quantity)} {lot.unit})
                  </small>
                </dd>
                <dt>{lot.date_type === 'DDM' ? 'DDM' : 'DLC'}</dt>
                <dd>
                  {lot.expiry_date ? formatDate(lot.expiry_date) : '—'}
                  {lot.is_expired && <span className="badge badge-danger">dépassée</span>}
                </dd>
                <dt>Emplacement</dt>
                <dd>
                  {lot.location_code} <small>(site {lot.site_code})</small>
                </dd>
                <dt>Réception</dt>
                <dd>
                  {lot.reception_date ? formatDate(lot.reception_date) : '—'}
                  {lot.supplier_code && ` · ${lot.supplier_code}`}
                  {lot.supplier_lot_number && ` · lot fournisseur ${lot.supplier_lot_number}`}
                </dd>
                {lot.block_reason && (
                  <>
                    <dt>Motif de blocage</dt>
                    <dd>{lot.block_reason}</dd>
                  </>
                )}
              </dl>
              <p className="hint">
                Libérer, bloquer, transférer ou corriger ce lot se fait sur sa fiche complète.
              </p>
            </>
          ),
        },
        { id: 'tracabilite', label: 'Traçabilité', content: <Trace lotNumber={lot.number} /> },
      ]}
      footer={
        <>
          <Link className="button secondary" to={`/lots/${lot.id}`}>
            <ExternalLink size={15} aria-hidden="true" /> Fiche complète
          </Link>
          <Link className="button danger" to={recall}>
            <ShieldAlert size={15} aria-hidden="true" /> Simuler un rappel de ce lot
          </Link>
        </>
      }
    />
  )
}
