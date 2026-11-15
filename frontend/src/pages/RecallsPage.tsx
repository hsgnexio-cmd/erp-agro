import { Download, ShieldAlert } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import type { Recall, RecallDetail } from '../api/quality'
import type { Paginated } from '../api/types'
import { type DataColumn, DataTable } from '../components/DataTable'
import { RecallImpactView } from '../components/RecallImpactView'
import { formatDate, formatDateTime } from '../format'
import { useApi } from '../hooks/useApi'

const COLUMNS: DataColumn<Recall>[] = [
  {
    id: 'number',
    header: 'Numéro',
    sortValue: (recall) => recall.number,
    cell: (recall) => <Link to={`/rappels/${recall.id}`}>{recall.number}</Link>,
  },
  {
    id: 'origin',
    header: "Lot d'origine",
    sortValue: (recall) => recall.origin_lot_number,
    cell: (recall) => (
      <>
        <span className="lot-number">{recall.origin_lot_number}</span> <small>{recall.origin_article_code}</small>
      </>
    ),
  },
  {
    id: 'reason',
    header: 'Motif',
    sortValue: (recall) => recall.reason,
    cell: (recall) => <span className="wrap">{recall.reason}</span>,
  },
  {
    id: 'blocked',
    header: 'Lots bloqués',
    numeric: true,
    sortValue: (recall) => recall.blocked_lot_count,
    cell: (recall) => recall.blocked_lot_count,
  },
  {
    id: 'created',
    header: 'Lancé le',
    sortValue: (recall) => recall.created_at,
    cell: (recall) => (
      <>
        {formatDateTime(recall.created_at)}
        {recall.created_by_name && ` par ${recall.created_by_name}`}
      </>
    ),
  },
]

/** Saisie d'un numéro de lot pour ouvrir la simulation de rappel. */
export function RecallSimulationForm() {
  const navigate = useNavigate()
  const [lot, setLot] = useState('')
  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    navigate(`/rappels/simulation?lot=${encodeURIComponent(lot.trim().toUpperCase())}`)
  }
  return (
    <form className="filters search-hero" onSubmit={handleSubmit} aria-label="Simuler un rappel">
      <input
        aria-label="Lot à rappeler"
        placeholder="Numéro de lot, ex. LR-261025-0001"
        value={lot}
        onChange={(e) => setLot(e.target.value)}
        required
      />
      <button type="submit" className="danger">
        <ShieldAlert size={15} aria-hidden="true" /> Simuler un rappel
      </button>
    </form>
  )
}

export function RecallsPage() {
  const recalls = useApi<Paginated<Recall>>('/api/qualite/recalls/')
  const navigate = useNavigate()
  const results = recalls.data?.results ?? []
  const blockedLots = results.reduce((total, recall) => total + recall.blocked_lot_count, 0)
  const latest = results.reduce<Recall | null>(
    (last, recall) => (!last || recall.created_at > last.created_at ? recall : last),
    null,
  )

  return (
    <section>
      <h1>Rappels produit</h1>
      <p className="page-intro">
        Saisis le lot suspect pour simuler le rappel : la simulation ne modifie rien. Le rappel
        n'est lancé (lots bloqués) qu'après confirmation par la qualité. Tu peux aussi partir de la{' '}
        <Link to="/tracabilite">traçabilité</Link> d'un lot.
      </p>
      <RecallSimulationForm />
      {recalls.error && <p className="error">{recalls.error}</p>}
      {recalls.data && (
        <>
          <div className="cards summary">
            <div className="card">
              <strong>{recalls.data.count}</strong>
              <span>rappel(s) lancé(s)</span>
            </div>
            <div className="card">
              <strong>{blockedLots}</strong>
              <span>lot(s) bloqué(s) par ces rappels</span>
            </div>
            <div className="card">
              <strong>{latest ? formatDate(latest.created_at) : '—'}</strong>
              <span>dernier rappel{latest && ` (${latest.number})`}</span>
            </div>
          </div>
          <DataTable
            caption="Rappels lancés"
            rows={results}
            columns={COLUMNS}
            rowKey={(recall) => recall.id}
            onRowClick={(recall) => navigate(`/rappels/${recall.id}`)}
            empty="Aucun rappel lancé."
          />
        </>
      )}
    </section>
  )
}

export function RecallDetailPage() {
  const { id } = useParams()
  const recall = useApi<RecallDetail>(`/api/qualite/recalls/${id}/`)
  if (recall.error) return <p className="error">{recall.error}</p>
  if (!recall.data) return <p>Chargement…</p>
  const r = recall.data

  return (
    <section>
      <p>
        <Link to="/rappels">← Retour aux rappels</Link>
      </p>
      <div className="page-title">
        <h1>
          Rappel {r.number} <small>lot {r.origin_lot_number}</small>
        </h1>
        <a className="button" href={`/api/qualite/recalls/${r.id}/export/`}>
          <Download size={15} aria-hidden="true" /> Télécharger la liste des clients à prévenir (Excel)
        </a>
      </div>
      <p className="error-box">
        <strong>Motif :</strong> {r.reason}
        <br />
        Lancé le {formatDateTime(r.created_at)}
        {r.created_by_name && ` par ${r.created_by_name}`} · {r.blocked_lot_count} lot(s) bloqué(s)
      </p>
      <RecallImpactView impact={r.snapshot} />
    </section>
  )
}
