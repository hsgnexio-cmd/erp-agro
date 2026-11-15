import { useState } from 'react'
import { Link } from 'react-router'
import type { ServiceRate, ServiceRateRow } from '../api/sales'
import { type DataColumn, DataTable } from '../components/DataTable'
import { formatDate, formatDateTime, formatDecimal, todayIso } from '../format'
import { useApi } from '../hooks/useApi'

type Issue = ServiceRate['issues'][number]

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

/**
 * Barres horizontales du taux de service par enseigne, avec un repère vertical à l'objectif.
 * L'axe démarre à la dizaine inférieure au plus petit taux (et au plus à 90 %) : sinon, des taux
 * de 96 et 99 % auraient des barres presque identiques.
 */
function RateBars({ data }: { data: ServiceRate }) {
  const target = Number(data.target)
  const rows = [
    ...data.customers.map((row) => ({ key: String(row.customer), label: `${row.customer_code} – ${row.customer_name}`, row })),
    { key: 'total', label: 'Toutes enseignes', row: data.total },
  ]
  const rates = rows.filter((item) => item.row.rate !== null).map((item) => Number(item.row.rate))
  const floor = Math.min(90, Math.floor(Math.min(target, ...rates) / 10) * 10)
  const position = (value: number) => `${Math.max(0, ((value - floor) / (100 - floor)) * 100)}%`

  return (
    <div className="panel rate-chart">
      <div className="rate-axis" aria-hidden="true">
        <span />
        <span className="rate-axis-scale">
          <span>{floor} %</span>
          <span className="rate-axis-target" style={{ left: position(target) }}>
            objectif {formatDecimal(data.target)} % ▾
          </span>
        </span>
        <span />
      </div>
      <ul className="rate-bars" aria-label="Taux de service par enseigne">
        {rows.map(({ key, label, row }) => (
          <li key={key} className={key === 'total' ? 'rate-row rate-total' : 'rate-row'}>
            <span className="rate-label">{label}</span>
            <span className="rate-track" aria-hidden="true">
              {row.rate !== null && (
                <span
                  className={`rate-fill ${row.below_target ? 'rate-below' : 'rate-ok'}`}
                  style={{ width: position(Number(row.rate)) }}
                />
              )}
              <span className="rate-target" style={{ left: position(target) }} />
            </span>
            <span className="rate-value">
              <Rate row={row} />
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

const ISSUE_COLUMNS: DataColumn<Issue>[] = [
  {
    id: 'order',
    header: 'Commande',
    sortValue: (issue) => issue.order_number,
    cell: (issue) => <Link to={`/ventes/${issue.order}`}>{issue.order_number}</Link>,
  },
  { id: 'customer', header: 'Enseigne', sortValue: (issue) => issue.customer_code, cell: (issue) => issue.customer_code },
  {
    id: 'delivery',
    header: 'Livraison demandée',
    sortValue: (issue) => issue.requested_delivery_date,
    cell: (issue) => formatDate(issue.requested_delivery_date),
  },
  {
    id: 'problem',
    header: 'Problème',
    sortValue: (issue) => issue.problem,
    cell: (issue) => <span className="badge badge-danger">{issue.problem}</span>,
  },
  {
    id: 'ordered',
    header: 'Commandé',
    numeric: true,
    sortValue: (issue) => Number(issue.ordered),
    cell: (issue) => `${formatDecimal(issue.ordered)} u`,
  },
  {
    id: 'delivered',
    header: 'Livré',
    numeric: true,
    sortValue: (issue) => Number(issue.delivered),
    cell: (issue) => `${formatDecimal(issue.delivered)} u`,
  },
  {
    id: 'shipped',
    header: 'Expédiée le',
    sortValue: (issue) => issue.shipped_at,
    cell: (issue) => (issue.shipped_at ? formatDateTime(issue.shipped_at) : '—'),
  },
]

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
      <p className="page-intro">
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
          <div className="stat-strip" aria-label="Synthèse de la période">
            <div className="stat">
              <strong>{data.total.orders}</strong>
              <span>commande(s) comptée(s)</span>
            </div>
            <div className="stat">
              <strong>{data.total.perfect_orders}</strong>
              <span>livrée(s) complète(s) et à l'heure</span>
            </div>
            <div className={data.issues.length > 0 ? 'stat stat-danger' : 'stat'}>
              <strong>{data.issues.length}</strong>
              <span>commande(s) à expliquer</span>
            </div>
            <div className="stat">
              <strong>{data.total.pending_orders}</strong>
              <span>en cours, pas encore comptée(s)</span>
            </div>
          </div>

          {data.customers.length > 0 && <RateBars data={data} />}

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
            <div className="empty-state">
              <strong>Rien à expliquer</strong>
              <span>Toutes les commandes de la période ont été livrées complètes et à l'heure.</span>
            </div>
          ) : (
            <DataTable
              caption="Commandes à expliquer"
              rows={data.issues}
              columns={ISSUE_COLUMNS}
              rowKey={(issue) => issue.order}
            />
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
