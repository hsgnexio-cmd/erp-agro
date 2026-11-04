import type { Reception } from '../api/types'
import { LOT_STATUS_LABELS, formatDate, formatDateTime, formatDecimal } from '../format'
import { StatusBadge } from './StatusBadge'

/** Une réception et le résultat de ses contrôles : lots créés, conformes ou bloqués. */
export function ReceptionResult({ reception }: { reception: Reception }) {
  return (
    <article className={`reception ${reception.is_compliant ? 'ok' : 'nok'}`}>
      <h3>
        {reception.number}{' '}
        <small>
          {formatDateTime(reception.received_at)} · BL {reception.delivery_note_number}
          {reception.received_by_name && ` · ${reception.received_by_name}`}
        </small>
      </h3>
      <p>{reception.is_compliant ? '✅ Réception conforme' : '⚠️ Réception non conforme'}</p>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Article</th>
              <th className="num">Quantité</th>
              <th>Lot fournisseur</th>
              <th>DLC / DDM</th>
              <th className="num">Temp.</th>
              <th>Lot créé</th>
              <th>Contrôle</th>
            </tr>
          </thead>
          <tbody>
            {reception.lines.map((line) => (
              <tr key={line.id}>
                <td>{line.article_code}</td>
                <td className="num">
                  {formatDecimal(line.quantity)} {line.unit}
                </td>
                <td>{line.supplier_lot_number}</td>
                <td>{formatDate(line.expiry_date)}</td>
                <td className="num">
                  {line.temperature === null ? '—' : `${formatDecimal(line.temperature)} °C`}
                </td>
                <td>
                  {line.lot_number}{' '}
                  {line.lot_status && (
                    <StatusBadge
                      status={line.lot_status}
                      label={LOT_STATUS_LABELS[line.lot_status] ?? line.lot_status}
                    />
                  )}
                </td>
                <td className="wrap">
                  {line.is_compliant ? 'Conforme' : line.non_compliance_reasons}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  )
}
