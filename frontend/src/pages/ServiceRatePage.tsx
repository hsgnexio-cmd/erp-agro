import { useState } from 'react'
import { Link } from 'react-router'
import type { ServiceRate, ServiceRateRow } from '../api/sales'
import { formatDate, formatDateTime, formatDecimal, todayIso } from '../format'
import { useApi } from '../hooks/useApi'

function daysAgoIso(days: number): string {
  const date = new Date(`${todayIso()}T12:00:00`)
  date.setDate(date.getDate() - days)
  return date.toISOString().slice(0, 10)
}

/** Badge rouge sous l'objectif, vert au-dessus. */
function Rate({ row }: { row: ServiceRateRow }) {
  if (row.rate === null) return <>—</>
  return (
    <span className={`badge ${row.below_target ? 'badge-danger' : 'badge-ok'}`}>
      {formatDecimal(row.rate)} %
    </span>
  )
}

/** Taux de service = quantité livrée complète et à l'heure ÷ quantité commandée. */
export function ServiceRatePage() {
  const [start, setStart] = useState(daysAgoIso(29))
  // Jusqu'à J+7 : les commandes livrées demain sont souvent déjà expédiées
  const [end, setEnd] = useState(daysAgoIso(-7))
  const { data, error } = useApi<ServiceRate>(`/api/ventes/service-rate/?start=${start}&end=${end}`)

  return (
    <section>
      <div className="page-title">
        <h1>Taux de service</h1>
        <div className="actions">
          <Link to="/expeditions">Bons de livraison</Link>
        </div>
      </div>
      <p className="hint">
        Quantité livrée complète et à l'heure ÷ quantité commandée, pour les commandes dont la
        livraison demandée tombe dans la période (hors commandes annulées). « À l'heure » :
        expédiée au plus tard la veille de la livraison (transport en J+1). Une commande pas encore
        expédiée mais encore dans les temps est « en cours » et n'est pas comptée. Objectif :{' '}
        {data ? formatDecimal(data.target) : '98,5'} % ; les pénalités des enseignes ne sont pas
        calculées.
      </p>
      <div className="filters">
        <label className="stacked">
          Livraisons du
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label className="stacked">
          au
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Enseigne</th>
                  <th className="num">Commandes</th>
                  <th className="num">Parfaites</th>
                  <th className="num">Commandé</th>
                  <th className="num">Livré à l'heure</th>
                  <th className="num">Livré en retard</th>
                  <th className="num">Non livré</th>
                  <th className="num">Taux de service</th>
                  <th className="num">En cours</th>
                </tr>
              </thead>
              <tbody>
                {data.customers.length === 0 && (
                  <tr>
                    <td colSpan={9}>Aucune commande sur cette période.</td>
                  </tr>
                )}
                {data.customers.map((row) => (
                  <tr key={row.customer}>
                    <td>
                      {row.customer_code} – {row.customer_name}
                    </td>
                    <ServiceRateCells row={row} target={data.target} />
                  </tr>
                ))}
              </tbody>
              {data.customers.length > 0 && (
                <tfoot>
                  <tr>
                    <th>Total</th>
                    <ServiceRateCells row={data.total} target={data.target} />
                  </tr>
                </tfoot>
              )}
            </table>
          </div>

          <h2>Commandes à expliquer</h2>
          {data.issues.length === 0 ? (
            <p>Toutes les commandes de la période ont été livrées complètes et à l'heure.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Commande</th>
                    <th>Enseigne</th>
                    <th>Livraison demandée</th>
                    <th>Problème</th>
                    <th className="num">Commandé</th>
                    <th className="num">Livré</th>
                    <th>Expédiée le</th>
                  </tr>
                </thead>
                <tbody>
                  {data.issues.map((issue) => (
                    <tr key={issue.order}>
                      <td>
                        <Link to={`/ventes/${issue.order}`}>{issue.order_number}</Link>
                      </td>
                      <td>{issue.customer_code}</td>
                      <td>{formatDate(issue.requested_delivery_date)}</td>
                      <td>{issue.problem}</td>
                      <td className="num">{formatDecimal(issue.ordered)} u</td>
                      <td className="num">{formatDecimal(issue.delivered)} u</td>
                      <td>{issue.shipped_at ? formatDateTime(issue.shipped_at) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  )
}

function ServiceRateCells({ row, target }: { row: ServiceRateRow; target: string }) {
  return (
    <>
      <td className="num">{row.orders}</td>
      <td className="num">{row.perfect_orders}</td>
      <td className="num">{formatDecimal(row.ordered)} u</td>
      <td className="num">{formatDecimal(row.on_time)} u</td>
      <td className="num">{formatDecimal(row.late)} u</td>
      <td className="num">{formatDecimal(row.missing)} u</td>
      <td className="num" title={`Objectif ${formatDecimal(target)} %`}>
        <Rate row={row} />
      </td>
      <td className="num">{row.pending_orders}</td>
    </>
  )
}
