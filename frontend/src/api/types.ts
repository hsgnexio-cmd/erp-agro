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
