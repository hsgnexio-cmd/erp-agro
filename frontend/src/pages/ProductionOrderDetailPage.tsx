import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { ProductionOrderDetail } from '../api/production'
import { useAuth } from '../auth/context'
import { PRODUCTION_ROLES, hasRole } from '../auth/roles'
import { ErrorList } from '../components/ErrorList'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, formatDateTime, formatDecimal } from '../format'
import { useApi } from '../hooks/useApi'

export function ProductionOrderDetailPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const [version, setVersion] = useState(0)
  const order = useApi<ProductionOrderDetail>(`/api/production/orders/${id}/?v=${version}`)
  const [errors, setErrors] = useState<string[]>([])

  if (order.error) return <p className="error">{order.error}</p>
  if (!order.data) return <p>Chargement…</p>
  const o = order.data
  const canManage = hasRole(user, PRODUCTION_ROLES)

  async function run(action: 'launch' | 'cancel' | 'close', question?: string) {
    if (question && !window.confirm(question)) return
    setErrors([])
    try {
      await apiPost(`/api/production/orders/${id}/${action}/`)
      setVersion((v) => v + 1)
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  const report = o.yield_report

  return (
    <section>
      <p>
        <Link to="/production">← Retour aux ordres de fabrication</Link>
      </p>
      <div className="page-title">
        <h1>
          {o.number} <small>{o.article_code} – {o.article_name}</small>
        </h1>
        <StatusBadge status={o.status} label={o.status_label} />
      </div>

      {canManage && (
        <div className="actions">
          {o.status === 'planifie' && (
            <button type="button" onClick={() => void run('launch')}>
              Lancer l'OF
            </button>
          )}
          {o.status === 'lance' && (
            <Link to={`/production/${o.id}/declaration`} className="button">
              Déclarer une production
            </Link>
          )}
          {o.status === 'lance' && o.declarations.length > 0 && (
            <button
              type="button"
              className="secondary"
              onClick={() => void run('close', 'Clôturer l’OF ? Plus aucune déclaration possible.')}
            >
              Clôturer l'OF
            </button>
          )}
          {['planifie', 'lance'].includes(o.status) && o.declarations.length === 0 && (
            <button
              type="button"
              className="danger"
              onClick={() => void run('cancel', 'Annuler cet OF ?')}
            >
              Annuler
            </button>
          )}
        </div>
      )}
      <ErrorList messages={errors} />

      <dl className="details">
        <dt>Date prévue</dt>
        <dd>
          {formatDate(o.planned_date)} (ordre {o.sequence} dans la journée)
        </dd>
        <dt>Ligne</dt>
        <dd>{o.line_code ?? `Cuisine de l'usine ${o.site_code}`}</dd>
        <dt>Quantité</dt>
        <dd>
          {formatDecimal(o.produced_quantity)} produit(s) sur {formatDecimal(o.planned_quantity)}{' '}
          {o.unit} prévu(s)
        </dd>
        <dt>Sortie</dt>
        <dd>{o.output_location_code} (en quarantaine jusqu'à la libération qualité)</dd>
        <dt>Allergènes</dt>
        <dd>{o.allergens.join(', ') || 'Aucun'}</dd>
        {o.comment && (
          <>
            <dt>Commentaire</dt>
            <dd>{o.comment}</dd>
          </>
        )}
      </dl>

      <h2>Besoins théoriques pour la quantité prévue</h2>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Composant</th>
              <th>Désignation</th>
              <th className="num">Net</th>
              <th className="num">Brut (avec pertes)</th>
            </tr>
          </thead>
          <tbody>
            {o.needs.map((need) => (
              <tr key={need.component}>
                <td>{need.component_code}</td>
                <td>{need.component_name}</td>
                <td className="num">
                  {formatDecimal(need.net)} {need.unit}
                </td>
                <td className="num">
                  {formatDecimal(need.gross)} {need.unit}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {o.declarations.length > 0 && (
        <>
          <h2>Déclarations</h2>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Lot fabriqué</th>
                  <th className="num">Quantité</th>
                  <th>Par</th>
                  <th>Écarts au FEFO</th>
                </tr>
              </thead>
              <tbody>
                {o.declarations.map((d) => (
                  <tr key={d.id}>
                    <td>{formatDateTime(d.declared_at)}</td>
                    <td>
                      <Link to={`/lots/${d.lot}`}>{d.lot_number}</Link>
                    </td>
                    <td className="num">
                      {formatDecimal(d.quantity)} {o.unit}
                    </td>
                    <td>{d.user_name ?? '—'}</td>
                    <td className="wrap">
                      {d.fefo_deviations.length === 0
                        ? 'Aucun'
                        : d.fefo_deviations.map((dev) => (
                            <div key={dev.lot_number}>
                              {dev.lot_number} au lieu de {dev.proposed.join(', ') || '—'} :{' '}
                              <em>{dev.justification}</em>
                            </div>
                          ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2>
            Rendement matière{' '}
            {report.mass_yield !== null && (
              <span className={`badge badge-${report.below_target ? 'danger' : 'ok'}`}>
                {formatDecimal(report.mass_yield)} % (objectif {formatDecimal(report.target)} %)
              </span>
            )}
          </h2>
          <p className="hint">
            Théorique = besoins de la nomenclature (pertes comprises) pour les{' '}
            {formatDecimal(report.produced)} {o.unit} produit(s). Rendement = théorique ÷ réel, sur
            les composants en kg et en litres.
          </p>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Composant</th>
                  <th className="num">Théorique</th>
                  <th className="num">Réel</th>
                  <th className="num">Écart</th>
                </tr>
              </thead>
              <tbody>
                {report.components.map((row) => {
                  const gap = row.gap_pct === null ? null : Number(row.gap_pct)
                  return (
                    <tr key={row.component_code}>
                      <td>{row.component_code}</td>
                      <td className="num">
                        {formatDecimal(row.theoretical)} {row.unit}
                      </td>
                      <td className="num">
                        {formatDecimal(row.actual)} {row.unit}
                      </td>
                      <td className={`num ${gap !== null && Math.abs(gap) > 4 ? 'negative' : ''}`}>
                        {gap === null ? '—' : `${gap > 0 ? '+' : ''}${formatDecimal(row.gap_pct)} %`}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
