// Formes des données des prévisions de vente (phase 9a)

export interface ForecastWeek {
  /** Lundi de la semaine (AAAA-MM-JJ) */
  week: string
  /** Numéro de semaine ISO, ex. "S46" */
  label: string
}

export interface ForecastAdjustmentInfo {
  id: number
  /** Quantité saisie par le commercial, qui remplace le calcul */
  quantity: string
  reason: string
  created_at: string
  created_by_name: string
}

export interface ForecastCell {
  week: string
  /** Moyenne pondérée des 4 dernières semaines, arrondie au colis de 12 */
  base: string
  promotion: number | null
  promo_coefficient: string | null
  promo_quantity: string | null
  adjustment: ForecastAdjustmentInfo | null
  /** Quantité retenue : correction, sinon promotion, sinon base */
  quantity: string
}

export interface ForecastRow {
  customer: number
  customer_code: string
  article: number
  article_code: string
  article_name: string
  cells: ForecastCell[]
}

export interface Forecast {
  computed_at: string
  current_week: string
  weeks: ForecastWeek[]
  rows: ForecastRow[]
}

export interface Promotion {
  id: number
  customer: number
  customer_code: string
  article: number
  article_code: string
  article_name: string
  first_week: string
  first_week_label: string
  last_week: string
  last_week_label: string
  coefficient: string
  announced_on: string
  notice_days: number
  /** Annoncée moins de 6 semaines avant son début */
  late_notice: boolean
  comment: string
  created_at: string
  created_by_name: string
  cancelled_at: string | null
  cancelled_by_name: string
  cancel_reason: string
}

export interface ForecastVersion {
  id: number
  number: string
  created_at: string
  created_by_name: string
  source: 'auto' | 'manuel'
  source_label: string
  first_week: string
  first_week_label: string
  comment: string
  line_count: number
  total_quantity: string | null
}

export interface AccuracyWeek {
  week: string
  label: string
  version_number: string
  version_created_at: string
  forecast: string
  actual: string
  abs_error: string
  accuracy: string | null
  /** Faux pour la semaine en cours (commandes pas toutes reçues) */
  complete: boolean
}

export interface Accuracy {
  start: string
  end: string
  target: string
  accuracy: string | null
  weeks: AccuracyWeek[]
}
