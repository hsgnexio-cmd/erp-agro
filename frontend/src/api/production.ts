// Formes des données de production : lignes, ordres de fabrication, planning

export interface ProductionLine {
  id: number
  code: string
  name: string
  site: number
  site_code: string
  family_codes: string[]
  formats: number[]
  capacity_per_hour: number
  active: boolean
}

export type OrderStatus = 'planifie' | 'lance' | 'termine' | 'annule'

export interface ProductionOrder {
  id: number
  number: string
  article: number
  article_code: string
  article_name: string
  article_type: string
  unit: string
  planned_quantity: string
  planned_date: string
  sequence: number
  site: number
  site_code: string
  line: number | null
  line_code: string | null
  output_location_code: string
  status: OrderStatus
  status_label: string
  comment: string
  produced_quantity: string
  mass_yield: string | null
}

export interface Need {
  component: number
  component_code: string
  component_name: string
  unit: string
  net: string
  gross: string
}

export interface Declaration {
  id: number
  lot: number
  lot_number: string
  quantity: string
  declared_at: string
  user_name: string | null
  comment: string
  fefo_deviations: {
    article_code: string
    lot_number: string
    proposed: string[]
    justification: string
  }[]
}

export interface YieldReport {
  produced: string
  mass_yield: string | null
  below_target: boolean
  target: string
  components: {
    component_code: string
    unit: string
    theoretical: string
    actual: string
    gap_pct: string | null
  }[]
}

export interface ProductionOrderDetail extends ProductionOrder {
  needs: Need[]
  declarations: Declaration[]
  yield_report: YieldReport
  allergens: string[]
  created_by_name: string | null
  launched_at: string | null
  closed_at: string | null
}

export interface ProposalLot {
  lot: number
  lot_number: string
  expiry_date: string | null
  location: number
  location_code: string
  available: string
  suggested: string
}

export interface ProposalRow {
  component: number
  component_code: string
  component_name: string
  unit: string
  need: string
  missing: string
  lots: ProposalLot[]
}

export interface PlanningOrder {
  id: number
  number: string
  article_code: string
  quantity: string
  status: OrderStatus
  status_label: string
  sequence: number
  hours: string
  allergens: string[]
}

export interface PlanningCell {
  date: string
  hours: string
  warnings: string[]
  orders: PlanningOrder[]
}

export interface Planning {
  week_start: string
  days: string[]
  capacity_hours: string
  lines: {
    line: number
    line_code: string
    line_name: string
    site_code: string
    capacity_per_hour: number
    cells: PlanningCell[]
  }[]
}
