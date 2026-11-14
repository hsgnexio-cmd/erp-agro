import { TriangleAlert } from 'lucide-react'
import { type ReactNode, useState } from 'react'
import { Link } from 'react-router'
import type { Planning } from '../api/production'
import { StatusBadge } from '../components/StatusBadge'
import { formatDecimal, todayIso } from '../format'
import { useApi } from '../hooks/useApi'

const DAY_NAMES = ['Lun.', 'Mar.', 'Mer.', 'Jeu.', 'Ven.', 'Sam.', 'Dim.']

function shiftWeek(isoDate: string, weeks: number): string {
  const date = new Date(`${isoDate}T12:00:00`)
  date.setDate(date.getDate() + weeks * 7)
  return date.toISOString().slice(0, 10)
}

/** Charge d'une journée par rapport à la capacité de la ligne : verte, orange à 85 %, rouge au-delà. */
function LoadBar({ hours, capacity, children }: { hours: number; capacity: number; children: ReactNode }) {
  const rate = capacity > 0 ? (hours / capacity) * 100 : 0
  const tone = rate > 100 ? 'danger' : rate >= 85 ? 'warn' : 'ok'
  return (
    <div className="planning-load">
      <div className="load-text">
        <span>{children}</span>
        <span className={`load-rate load-text-${tone}`}>{Math.round(rate)} %</span>
      </div>
      <div className="load-track" aria-hidden="true">
        <span className={`load-fill load-${tone}`} style={{ width: `${Math.min(100, rate)}%` }} />
      </div>
    </div>
  )
}

/** Planning de la semaine par ligne : charge, capacité, ordre des allergènes. */
export function PlanningPage() {
  const [week, setWeek] = useState(todayIso())
  const [site, setSite] = useState('')
  const planning = useApi<Planning>(`/api/production/planning/?week=${week}&site=${site}`)
  const capacity = Number(planning.data?.capacity_hours ?? 0)

  return (
    <section>
      <h1>Planning de production</h1>
      <div className="filters">
        <button type="button" className="secondary" onClick={() => setWeek(shiftWeek(week, -1))}>
          ← Semaine précédente
        </button>
        <button type="button" className="secondary" onClick={() => setWeek(todayIso())}>
          Cette semaine
        </button>
        <button type="button" className="secondary" onClick={() => setWeek(shiftWeek(week, 1))}>
          Semaine suivante →
        </button>
        <select aria-label="Usine" value={site} onChange={(e) => setSite(e.target.value)}>
          <option value="">Toutes les usines</option>
          <option value="NAN">NAN – Plats chauds</option>
          <option value="REN">REN – Traiteur froid</option>
        </select>
      </div>
      {planning.error && <p className="error">{planning.error}</p>}
      {planning.data && (
        <>
          <p className="hint">
            Capacité : {formatDecimal(planning.data.capacity_hours)} h par jour et par ligne (2
            équipes). Les OF d'une journée sont dans l'ordre de passage ; la barre montre la charge
            de la journée par rapport à cette capacité.
          </p>
          <div className="table-wrapper">
            <table className="planning">
              <thead>
                <tr>
                  <th>Ligne</th>
                  {planning.data.days.map((day, index) => (
                    <th key={day}>
                      {DAY_NAMES[index]} {day.slice(8, 10)}/{day.slice(5, 7)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {planning.data.lines.map((line) => (
                  <tr key={line.line}>
                    <th>
                      {line.line_code}
                      <br />
                      <small>{line.line_name}</small>
                    </th>
                    {line.cells.map((cell) => (
                      <td
                        key={cell.date}
                        className={`planning-cell ${cell.warnings.length > 0 ? 'has-warning' : ''} ${cell.closed ? 'closed-day' : ''}`}
                        title={cell.closed ? `Usine fermée : ${cell.closed}` : undefined}
                      >
                        {cell.closed && cell.orders.length === 0 && <small className="closed-label">{cell.closed}</small>}
                        {cell.orders.map((order) => (
                          <div key={order.id} className="planning-order">
                            <Link to={`/production/${order.id}`}>{order.number}</Link>{' '}
                            <StatusBadge status={order.status} label={order.status_label} />
                            <div>
                              {order.article_code}
                              <br />
                              <small>
                                {formatDecimal(order.quantity)} u · {formatDecimal(order.hours)} h
                              </small>
                            </div>
                          </div>
                        ))}
                        {Number(cell.hours) > 0 && (
                          <LoadBar hours={Number(cell.hours)} capacity={capacity}>
                            Charge : {formatDecimal(cell.hours)} h
                          </LoadBar>
                        )}
                        {cell.warnings.map((warning) => (
                          <div key={warning} className="planning-warning" role="note">
                            <TriangleAlert size={14} aria-hidden="true" /> {warning}
                          </div>
                        ))}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
