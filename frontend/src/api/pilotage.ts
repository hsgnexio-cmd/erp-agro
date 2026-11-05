// Formes des données du pilotage : indicateurs du tableau de bord

export type IndicatorStatus = 'ok' | 'alerte' | 'sans_donnee' | 'indisponible'

export interface Indicator {
  code: string
  label: string
  /** "%", "% du CA", "jours" ou "s" */
  unit: string
  definition: string
  /** Filtres pris en compte par cet indicateur */
  filters: string[]
  value: string | null
  target: string
  target_min: string | null
  target_max: string | null
  status: IndicatorStatus
  detail: string
}

export interface IndicatorWeek {
  start: string
  end: string
  label: string
  values: Record<string, string | null>
}

export interface Indicators {
  start: string
  end: string
  indicators: Indicator[]
  weeks: IndicatorWeek[]
}
