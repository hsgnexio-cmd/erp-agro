import { Link } from 'react-router'
import type { TraceNode } from '../api/quality'
import { formatDate, formatDecimal } from '../format'
import { StatusBadge } from './StatusBadge'

type Direction = 'amont' | 'aval'

/** Arbre de traçabilité : chaque lot, puis en retrait les lots qui lui sont liés. */
export function TraceTree({ node, direction }: { node: TraceNode; direction: Direction }) {
  return (
    <ul className="trace-tree">
      <TraceItem node={node} direction={direction} parent={null} />
    </ul>
  )
}

function quantityLabel(node: TraceNode, direction: Direction, parent: TraceNode | null) {
  if (node.quantity === null || parent === null) return null
  // Amont : quantité de CE lot consommée par le parent (unité de ce lot).
  // Aval : quantité du PARENT utilisée pour fabriquer ce lot (unité du parent).
  return direction === 'amont'
    ? `consommé : ${formatDecimal(node.quantity)} ${node.unit}`
    : `a utilisé ${formatDecimal(node.quantity)} ${parent.unit} de ${parent.lot_number}`
}

function TraceItem({
  node,
  direction,
  parent,
}: {
  node: TraceNode
  direction: Direction
  parent: TraceNode | null
}) {
  const quantity = quantityLabel(node, direction, parent)
  return (
    <li>
      <div className="trace-node">
        <Link to={`/lots/${node.lot}`}>{node.lot_number}</Link>
        <span>
          {node.article_code} <small>{node.article_name}</small>
        </span>
        <StatusBadge status={node.status} label={node.status_label} />
        {node.expiry_date && <small>DLC/DDM {formatDate(node.expiry_date)}</small>}
        {quantity && <small className="trace-qty">{quantity}</small>}
      </div>
      {node.shipments.length > 0 && (
        <ul className="trace-shipments">
          {node.shipments.map((s) => (
            <li key={s.warehouse_code}>
              🚚 {s.customer_code} – {s.warehouse_name} : {formatDecimal(s.quantity)} {node.unit}{' '}
              <small>(dernière livraison le {formatDate(s.last_shipped)})</small>
            </li>
          ))}
        </ul>
      )}
      {node.children.length > 0 && (
        <ul>
          {node.children.map((child) => (
            <TraceItem key={child.lot} node={child} direction={direction} parent={node} />
          ))}
        </ul>
      )}
    </li>
  )
}
