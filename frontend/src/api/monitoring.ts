// Formes des données de la surveillance (températures, inventaires, alertes)

export interface TemperatureReading {
  id: number
  location: number
  location_code: string
  location_name: string
  site_code: string
  temperature: string
  measured_at: string
  min_allowed: string | null
  max_allowed: string | null
  is_compliant: boolean
  user_name: string | null
  comment: string
}

export interface TemperatureReadingResult extends TemperatureReading {
  blocked_lots: string[]
  alert: string | null
}

export interface ColdRoomStatus {
  location: number
  location_code: string
  location_name: string
  site_code: string
  min_allowed: string | null
  max_allowed: string | null
  last_reading: TemperatureReading | null
}

export interface InventoryLine {
  id: number
  lot: number
  lot_number: string
  article_code: string
  article_name: string
  unit: string
  expiry_date: string | null
  location: number
  location_code: string
  /** Caché (null) pendant le comptage à l'aveugle */
  expected_quantity: string | null
  counted_quantity: string | null
  difference: string | null
  added_during_count: boolean
}

export interface Inventory {
  id: number
  number: string
  site: number
  site_code: string
  location: number | null
  location_code: string | null
  status: 'en_cours' | 'valide' | 'annule'
  status_label: string
  comment: string
  opened_at: string
  opened_by_name: string | null
  closed_at: string | null
  closed_by_name: string | null
  line_count: number
}

export interface InventoryDetail extends Inventory {
  lines: InventoryLine[]
}

export interface Alert {
  id: number
  alert_type: string
  alert_type_label: string
  level: 'attention' | 'critique'
  level_label: string
  message: string
  lot: number | null
  lot_number: string | null
  location: number | null
  location_code: string | null
  created_at: string
  is_open: boolean
  resolved_at: string | null
  resolved_by_name: string | null
  resolution_comment: string
}
