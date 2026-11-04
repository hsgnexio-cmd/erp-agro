import { Link, useParams } from 'react-router'
import type { Recall, RecallDetail } from '../api/quality'
import type { Paginated } from '../api/types'
import { RecallImpactView } from '../components/RecallImpactView'
import { formatDateTime } from '../format'
import { useApi } from '../hooks/useApi'

export function RecallsPage() {
  const recalls = useApi<Paginated<Recall>>('/api/qualite/recalls/')
  return (
    <section>
      <h1>Rappels produit</h1>
      <p className="hint">
        Pour lancer un rappel : menu <Link to="/tracabilite">Traçabilité</Link> → numéro du lot →
        « Simuler un rappel ».
      </p>
      {recalls.data && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Numéro</th>
                <th>Lot d'origine</th>
                <th>Motif</th>
                <th className="num">Lots bloqués</th>
                <th>Lancé le</th>
              </tr>
            </thead>
            <tbody>
              {recalls.data.results.length === 0 && (
                <tr>
                  <td colSpan={5}>Aucun rappel lancé.</td>
                </tr>
              )}
              {recalls.data.results.map((recall) => (
                <tr key={recall.id}>
                  <td>
                    <Link to={`/rappels/${recall.id}`}>{recall.number}</Link>
                  </td>
                  <td>
                    {recall.origin_lot_number} <small>{recall.origin_article_code}</small>
                  </td>
                  <td className="wrap">{recall.reason}</td>
                  <td className="num">{recall.blocked_lot_count}</td>
                  <td>
                    {formatDateTime(recall.created_at)}
                    {recall.created_by_name && ` par ${recall.created_by_name}`}
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
      <h1>
        Rappel {r.number} <small>lot {r.origin_lot_number}</small>
      </h1>
      <p className="error-box">
        <strong>Motif :</strong> {r.reason}
        <br />
        Lancé le {formatDateTime(r.created_at)}
        {r.created_by_name && ` par ${r.created_by_name}`} · {r.blocked_lot_count} lot(s) bloqué(s)
      </p>
      <div className="actions">
        <a className="button" href={`/api/qualite/recalls/${r.id}/export/`}>
          ⬇ Télécharger la liste des clients à prévenir (Excel)
        </a>
      </div>
      <RecallImpactView impact={r.snapshot} />
    </section>
  )
}
