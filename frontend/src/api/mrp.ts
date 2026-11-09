// Formes des données du calcul des besoins (MRP, phase 9c)

export interface MrpWeek {
  week: string
  label: string
  /** Origine de la production prévue : OF, plan brouillon ou prévision */
  source: string
}

export interface MrpProposal {
  article: number
  article_code: string
  article_name: string
  article_type: 'MP' | 'EM'
  unit: string
  supplier: number | null
  supplier_code: string | null
  supplier_name: string | null
  lead_time_days: number | null
  week: string
  week_label: string
  need_date: string
  order_date: string | null
  /** La date de commande (besoin − délai fournisseur) est déjà passée */
  late: boolean
  net: string
  quantity: string
  min_order_quantity: string | null
  raised_to_minimum: boolean
  unit_price: string | null
  amount: string | null
}

export interface MrpArticle {
  article: number
  article_code: string
  article_name: string
  unit: string
  stock: string
  weeks: { week: string; gross: string; receipts: string; planned: string; projected: string }[]
}

export interface Mrp {
  computed_at: string
  weeks: MrpWeek[]
  proposals: MrpProposal[]
  articles: MrpArticle[]
}

export interface CreatedPurchaseOrder {
  id: number
  number: string
  supplier_code: string
  expected_delivery_date: string
  line_count: number
}
