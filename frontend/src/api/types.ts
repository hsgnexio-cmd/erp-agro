// Formes des données renvoyées par l'API (voir backend/referentiel/serializers.py)

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface User {
  id: number
  username: string
  first_name: string
  last_name: string
  is_superuser: boolean
  roles: string[]
}

export type ArticleType = 'MP' | 'SF' | 'PF' | 'EM'

export interface Article {
  id: number
  code: string
  name: string
  article_type: ArticleType
  article_type_label: string
  unit: string
  category: number | null
  category_code: string | null
  recipe: number | null
  recipe_code: string | null
  brand_customer: number | null
  brand_code: string
  format_size: number | null
  shelf_life_days: number | null
  date_type: string
  storage_temperature_class: string
  technical_sheet: string
  specifications: string
  allergens: number[]
  allergen_names: string[]
  has_bom: boolean
  active: boolean
}

export interface BomLine {
  id: number
  bom: number
  component: number
  component_code: string
  component_name: string
  component_type: ArticleType
  quantity: string
  unit: string
  loss_rate: string
  gross_quantity: string
}

export interface Bom {
  id: number
  article: number
  article_code: string
  article_name: string
  article_unit: string
  base_quantity: string
  comment: string
  lines: BomLine[]
}

export interface Supplier {
  id: number
  code: string
  name: string
  city: string
  country: string
  email: string
  phone: string
  lead_time_days: number
  category_codes: string[]
  audited: boolean
  last_audit_date: string | null
  active: boolean
}

export interface Customer {
  id: number
  code: string
  name: string
  customer_type: string
  customer_type_label: string
  sells_brand: boolean
  sells_private_label: boolean
  min_remaining_shelf_life_pct: string
  warehouse_count: number
  active: boolean
}

export interface Site {
  id: number
  code: string
  name: string
  site_type: string
  site_type_label: string
  city: string
  active: boolean
}

export interface Location {
  id: number
  site: number
  site_code: string
  code: string
  name: string
  temperature_class: string
  temperature_class_label: string
  min_temperature: string | null
  max_temperature: string | null
  active: boolean
}

// --- Achats -----------------------------------------------------------------

export type PurchaseOrderStatus =
  | 'brouillon'
  | 'envoyee'
  | 'partiellement_recue'
  | 'soldee'
  | 'annulee'

export interface PurchaseOrderLine {
  id: number
  article: number
  article_code: string
  article_name: string
  article_date_type: string
  article_temperature_class: string
  quantity: string
  unit: string
  unit_price: string
  amount: string
  received_quantity: string
}

export interface PurchaseOrder {
  id: number
  number: string
  supplier: number
  supplier_code: string
  supplier_name: string
  delivery_site: number
  delivery_site_code: string
  order_date: string
  expected_delivery_date: string
  status: PurchaseOrderStatus
  status_label: string
  comment: string
  created_by_name: string | null
  created_at: string
  sent_at: string | null
  total_amount: string
  lines: PurchaseOrderLine[]
  reception_ids: number[]
}

export interface CatalogItem {
  article: number
  article_code: string
  article_name: string
  unit: string
  min_order_quantity: string | null
  unit_price: string | null
}

export interface ReceptionLine {
  id: number
  order_line: number
  article_code: string
  article_name: string
  unit: string
  quantity: string
  supplier_lot_number: string
  expiry_date: string | null
  temperature: string | null
  appearance_ok: boolean
  is_compliant: boolean
  non_compliance_reasons: string
  lot: number | null
  lot_number: string | null
  lot_status: string | null
}

export interface Reception {
  id: number
  number: string
  order: number
  order_number: string
  supplier_name: string
  received_at: string
  received_by_name: string | null
  delivery_note_number: string
  documents_ok: boolean
  location: number
  location_code: string
  comment: string
  is_compliant: boolean
  lines: ReceptionLine[]
}

// --- Stocks -----------------------------------------------------------------

export type LotStatus = 'libere' | 'bloque' | 'quarantaine' | 'detruit'

export interface Lot {
  id: number
  number: string
  article: number
  article_code: string
  article_name: string
  article_type: ArticleType
  unit: string
  supplier_code: string | null
  supplier_lot_number: string
  reception_date: string | null
  date_type: string
  expiry_date: string | null
  initial_quantity: string
  quantity: string
  location_code: string
  site_code: string
  status: LotStatus
  status_label: string
  block_reason: string
  reception_number: string | null
  created_at: string
}
