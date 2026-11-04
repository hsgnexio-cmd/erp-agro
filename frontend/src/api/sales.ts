// Formes des données de ventes : tarifs, commandes clients, messages EDI, expéditions

export interface SalePrice {
  id: number
  customer: number
  customer_code: string
  article: number
  article_code: string
  article_name: string
  unit_price: string
  valid_from: string
  valid_to: string | null
}

export interface CustomerOrderLine {
  id: number
  article: number
  article_code: string
  article_name: string
  quantity: string
  unit_price: string | null
  amount: string | null
  to_be_priced: boolean
  /** Quantité livrée, une fois la commande expédiée (sinon null) */
  shipped_quantity: string | null
}

export interface CustomerOrder {
  id: number
  number: string
  customer: number
  customer_code: string
  customer_name: string
  warehouse: number
  warehouse_code: string
  warehouse_name: string
  customer_reference: string
  received_at: string
  requested_delivery_date: string
  status: 'recue' | 'en_preparation' | 'expediee' | 'annulee'
  status_label: string
  source: 'edi' | 'manuel'
  source_label: string
  total_amount: string
  line_count: number
  to_be_priced: boolean
  comment: string
}

export interface CustomerOrderDetail extends CustomerOrder {
  lines: CustomerOrderLine[]
  edi_message_id: string | null
  created_by_name: string | null
  shipments: { id: number; number: string; status: ShipmentStatus; status_label: string }[]
}

export interface OrderableArticles {
  earliest_delivery_date: string
  articles: { article: number; article_code: string; article_name: string; unit_price: string | null }[]
}

export interface EdiMessage {
  id: number
  message_id: string
  customer_code: string | null
  received_at: string
  status: 'recu' | 'integre' | 'rejete'
  status_label: string
  errors: string[]
  payload: unknown
  order: { id: number; number: string } | null
}

// --- Préparation et expédition (partie 7b) ---

export interface PickingLot {
  lot: number
  lot_number: string
  expiry_date: string | null
  location: number
  location_code: string
  available: string
  suggested: string
}

export interface PickingLine {
  order_line: number
  article: number
  article_code: string
  article_name: string
  unit: string
  ordered: string
  min_expiry_date: string | null
  missing: string
  lots: PickingLot[]
  too_short: { lot_number: string; expiry_date: string | null; location_code: string; available: string }[]
}

export interface PickingProposal {
  order: number
  requested_delivery_date: string
  min_remaining_shelf_life_pct: string
  lines: PickingLine[]
}

export type ShipmentStatus = 'preparee' | 'expediee' | 'refusee' | 'annulee'

export interface Shipment {
  id: number
  number: string
  order: number
  order_number: string
  customer_code: string
  customer_name: string
  warehouse_code: string
  warehouse_name: string
  requested_delivery_date: string
  status: ShipmentStatus
  status_label: string
  prepared_at: string
  prepared_by_name: string | null
  carrier: string
  loading_temperature: string | null
  shipped_at: string | null
  shipped_by_name: string | null
  refusal_reason: string
  total_quantity: string
  pallet_count: number
  on_time: boolean | null
}

export interface Pallet {
  id: number
  sscc: string
  rank: number
  total_quantity: string
  lines: {
    id: number
    article_code: string
    article_name: string
    lot_number: string
    expiry_date: string | null
    quantity: string
  }[]
}

export interface ShipmentDetail extends Shipment {
  lines: {
    id: number
    order_line: number
    article_code: string
    article_name: string
    unit: string
    lot: number
    lot_number: string
    expiry_date: string | null
    location_code: string
    quantity: string
    fefo_justification: string
  }[]
  pallets: Pallet[]
  summary: {
    order_line: number
    article_code: string
    article_name: string
    ordered: string
    prepared: string
    missing: string
  }[]
}

export interface ServiceRateRow {
  ordered: string
  on_time: string
  late: string
  missing: string
  orders: number
  perfect_orders: number
  pending_orders: number
  rate: string | null
  below_target: boolean
}

export interface ServiceRate {
  start: string
  end: string
  target: string
  customers: (ServiceRateRow & { customer: number; customer_code: string; customer_name: string })[]
  total: ServiceRateRow
  issues: {
    order: number
    order_number: string
    customer_code: string
    requested_delivery_date: string
    problem: string
    ordered: string
    delivered: string
    shipped_at: string | null
  }[]
}
