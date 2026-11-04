// Formes des données qualité : traçabilité, rappels, allergènes

export interface TraceShipment {
  customer_code: string
  warehouse_code: string
  warehouse_name: string
  quantity: string
  last_shipped: string
}

export interface TraceNode {
  lot: number
  lot_number: string
  article_code: string
  article_name: string
  article_type: string
  unit: string
  status: string
  status_label: string
  expiry_date: string | null
  /** Quantité de ce lot consommée par le parent (amont) ou dans l'enfant (aval) */
  quantity: string | null
  shipments: TraceShipment[]
  children: TraceNode[]
}

export interface Traceability {
  upstream: TraceNode
  downstream: TraceNode
}

export interface ImpactLotInfo {
  id: number
  number: string
  article_code: string
  article_name: string
  article_type: string
  unit: string
  status: string
  status_label: string
  expiry_date: string | null
}

export interface ImpactLot extends ImpactLotInfo {
  level: number
  stock_total: string
  stock: { location_code: string; site_code: string; quantity: string }[]
}

export interface ImpactDelivery {
  lot_number: string
  article_code: string
  article_name: string
  unit: string
  expiry_date: string | null
  customer_code: string
  customer_name: string
  warehouse_code: string
  warehouse_name: string
  city: string
  quantity: string
  last_shipped: string
}

export interface RecallImpact {
  origin: ImpactLotInfo
  computed_at: string
  lots: ImpactLot[]
  deliveries: ImpactDelivery[]
  customers: { code: string; name: string; deliveries: number; quantities: Record<string, string> }[]
  lots_to_block: string[]
  blocked_lots?: string[]
}

export interface Recall {
  id: number
  number: string
  origin_lot: number
  origin_lot_number: string
  origin_article_code: string
  reason: string
  created_at: string
  created_by_name: string | null
  blocked_lot_count: number
}

export interface RecallDetail extends Recall {
  snapshot: RecallImpact
}

export interface ComputedAllergen {
  code: string
  name: string
  sources: string[][]
}
