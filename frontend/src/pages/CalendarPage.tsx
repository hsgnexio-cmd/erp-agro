import { useState } from 'react'
import type { CompanyCalendar } from '../api/calendar'
import { formatDate } from '../format'
import { useApi } from '../hooks/useApi'

const WEEKEND = ['samedi', 'dimanche']

/** Calendrier de l'entreprise : qui travaille quand, jours fériés, fermetures exceptionnelles. */
export function CalendarPage() {
  const [year, setYear] = useState(new Date().getFullYear())
  const { data, error } = useApi<CompanyCalendar>(`/api/referentiel/calendar/?year=${year}`)

  return (
    <section>
      <h1>Calendrier</h1>
      <p className="hint">
        Jours travaillés de chaque activité, jours fériés (calculés automatiquement) et fermetures
        exceptionnelles des sites. Les fermetures se saisissent dans l'administration (rôle admin).
        Ce calendrier sert à l'heure limite de commande, au taux de service, au plan de production,
        au planning et aux délais fournisseurs.
      </p>
      <div className="filters">
        <button type="button" className="secondary" onClick={() => setYear(year - 1)}>
          ← {year - 1}
        </button>
        <strong className="week-title">{year}</strong>
        <button type="button" className="secondary" onClick={() => setYear(year + 1)}>
          {year + 1} →
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <h2>Qui travaille quand</h2>
          <div className="table-wrapper">
            <table aria-label="Jours travaillés">
              <tbody>
                {data.rules.map((rule) => (
                  <tr key={rule.activity}>
                    <th>{rule.activity}</th>
                    <td>{rule.days}, hors jours fériés et fermetures du site</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2>Jours fériés {data.year}</h2>
          <div className="table-wrapper">
            <table aria-label="Jours fériés">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Jour</th>
                  <th>Férié</th>
                </tr>
              </thead>
              <tbody>
                {data.holidays.map((day) => (
                  <tr key={day.date}>
                    <td>{formatDate(day.date)}</td>
                    <td>
                      {day.weekday}{' '}
                      {WEEKEND.includes(day.weekday) && (
                        <small className="badge badge-neutral">tombe un week-end</small>
                      )}
                    </td>
                    <td>{day.label}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2>Fermetures exceptionnelles</h2>
          <div className="table-wrapper">
            <table aria-label="Fermetures exceptionnelles">
              <thead>
                <tr>
                  <th>Site</th>
                  <th>Du</th>
                  <th>Au</th>
                  <th>Motif</th>
                </tr>
              </thead>
              <tbody>
                {data.closures.length === 0 && (
                  <tr>
                    <td colSpan={4}>Aucune fermeture exceptionnelle cette année.</td>
                  </tr>
                )}
                {data.closures.map((closure) => (
                  <tr key={closure.id}>
                    <td>
                      {closure.site_code} <small>{closure.site_name}</small>
                    </td>
                    <td>{formatDate(closure.start_date)}</td>
                    <td>{formatDate(closure.end_date)}</td>
                    <td>{closure.reason}</td>
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
