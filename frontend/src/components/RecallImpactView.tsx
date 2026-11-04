import { Link } from 'react-router'
import type { RecallImpact } from '../api/quality'
import { formatDate, formatDateTime, formatDecimal } from '../format'
import { StatusBadge } from './StatusBadge'

const LEVELS = ["Lot d'origine", 'Niveau 1', 'Niveau 2', 'Niveau 3', 'Niveau 4']

/** Résultat d'un rappel : lots concernés, stocks restants, clients livrés. */
export function RecallImpactView({ impact }: { impact: RecallImpact }) {
  const finished = impact.lots.filter((lot) => lot.article_type === 'PF')
  return (
    <>
      <div className="cards summary">
        <div className="card">
          <strong>{impact.lots.length}</strong>
          <span>lot(s) concerné(s), dont {finished.length} de produit fini</span>
        </div>
        <div className="card">
          <strong>{impact.lots_to_block.length}</strong>
          <span>lot(s) avec du stock {impact.blocked_lots ? 'bloqué(s)' : 'à bloquer'}</span>
        </div>
        <div className="card">
          <strong>{impact.customers.length}</strong>
          <span>enseigne(s) livrée(s) à prévenir</span>
        </div>
      </div>
      <p className="hint">Calculé le {formatDateTime(impact.computed_at)}.</p>

      <h2>Lots concernés et stocks restants</h2>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Niveau</th>
              <th>Lot</th>
              <th>Article</th>
              <th>DLC / DDM</th>
              <th>Statut</th>
              <th>Stock restant</th>
            </tr>
          </thead>
          <tbody>
            {impact.lots.map((lot) => (
              <tr key={lot.id}>
                <td>{LEVELS[lot.level] ?? `Niveau ${lot.level}`}</td>
                <td>
                  <Link to={`/lots/${lot.id}`}>{lot.number}</Link>
                </td>
                <td>
                  {lot.article_code}
                  <br />
                  <small>{lot.article_name}</small>
                </td>
                <td>{formatDate(lot.expiry_date)}</td>
                <td>
                  <StatusBadge status={lot.status} label={lot.status_label} />
                </td>
                <td className="wrap">
                  {lot.stock.length === 0
                    ? '—'
                    : lot.stock.map((row) => (
                        <div key={row.location_code}>
                          {formatDecimal(row.quantity)} {lot.unit} en {row.location_code}
                        </div>
                      ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>Clients livrés</h2>
      {impact.deliveries.length === 0 ? (
        <p>Aucune livraison : rien n'est parti chez les clients.</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Enseigne</th>
                <th>Entrepôt</th>
                <th>Lot</th>
                <th>Article</th>
                <th>DLC</th>
                <th className="num">Quantité livrée</th>
                <th>Dernière livraison</th>
              </tr>
            </thead>
            <tbody>
              {impact.deliveries.map((d) => (
                <tr key={`${d.warehouse_code}-${d.lot_number}`}>
                  <td>
                    {d.customer_code} – {d.customer_name}
                  </td>
                  <td>
                    {d.warehouse_name} <small>({d.city})</small>
                  </td>
                  <td>{d.lot_number}</td>
                  <td>{d.article_code}</td>
                  <td>{formatDate(d.expiry_date)}</td>
                  <td className="num">
                    {formatDecimal(d.quantity)} {d.unit}
                  </td>
                  <td>{formatDate(d.last_shipped)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
