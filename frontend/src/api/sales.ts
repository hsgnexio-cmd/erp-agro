// Formes des données de ventes : tarifs, commandes clients, messages EDI

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
