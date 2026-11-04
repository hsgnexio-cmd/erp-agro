import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type {
  CustomerOrderDetail,
  PickingProposal,
  ServiceRate,
  ShipmentDetail,
} from '../api/sales'
import type { LotDetail } from '../api/types'
import { TEST_USER, mockApi, paginated, renderApp } from '../test/utils'

const STOREKEEPER = { ...TEST_USER, roles: ['magasinier'] }
const SALES = { ...TEST_USER, roles: ['commercial'] }
const QUALITY = { ...TEST_USER, roles: ['qualite'] }

const ORDER: CustomerOrderDetail = {
  id: 7,
  number: 'CC-2026-00007',
  customer: 2,
  customer_code: 'ENS2',
  customer_name: 'Marché Plus',
  warehouse: 5,
  warehouse_code: 'ENS2-E01',
  warehouse_name: 'Entrepôt Marché Plus Nantes',
  customer_reference: '',
  received_at: '2026-11-04T08:30:00Z',
  requested_delivery_date: '2026-11-06',
  status: 'recue',
  status_label: 'Reçue',
  source: 'edi',
  source_label: 'EDI',
  total_amount: '860.00',
  line_count: 1,
  to_be_priced: false,
  comment: '',
  lines: [
    {
      id: 1,
      article: 65,
      article_code: 'PF-PAT-LASBOL-BRE-300',
      article_name: 'Lasagnes bolognaise 300 g',
      quantity: '400.000',
      unit_price: '2.1500',
      amount: '860.00',
      to_be_priced: false,
      shipped_quantity: null,
    },
  ],
  edi_message_id: null,
  created_by_name: null,
  shipments: [],
}

const PROPOSAL: PickingProposal = {
  order: 7,
  requested_delivery_date: '2026-11-06',
  min_remaining_shelf_life_pct: '70.00',
  lines: [
    {
      order_line: 1,
      article: 65,
      article_code: 'PF-PAT-LASBOL-BRE-300',
      article_name: 'Lasagnes bolognaise 300 g',
      unit: 'u',
      ordered: '400.000',
      min_expiry_date: '2026-11-16',
      missing: '0.000',
      lots: [
        {
          lot: 31,
          lot_number: 'LF-261103-0001',
          expiry_date: '2026-11-17',
          location: 8,
          location_code: 'PFN-FRAIS-A',
          available: '300.000',
          suggested: '300.000',
        },
        {
          lot: 32,
          lot_number: 'LF-261104-0001',
          expiry_date: '2026-11-18',
          location: 8,
          location_code: 'PFN-FRAIS-A',
          available: '500.000',
          suggested: '100.000',
        },
      ],
      too_short: [
        {
          lot_number: 'LF-261101-0004',
          expiry_date: '2026-11-15',
          location_code: 'PFN-FRAIS-B',
          available: '60.000',
        },
      ],
    },
  ],
}

const SHIPMENT: ShipmentDetail = {
  id: 4,
  number: 'BL-2026-00004',
  order: 7,
  order_number: 'CC-2026-00007',
  customer_code: 'ENS2',
  customer_name: 'Marché Plus',
  warehouse_code: 'ENS2-E01',
  warehouse_name: 'Entrepôt Marché Plus Nantes',
  requested_delivery_date: '2026-11-06',
  status: 'preparee',
  status_label: 'Préparée',
  prepared_at: '2026-11-04T13:00:00Z',
  prepared_by_name: 'paul',
  carrier: '',
  loading_temperature: null,
  shipped_at: null,
  shipped_by_name: null,
  refusal_reason: '',
  total_quantity: '360.000',
  pallet_count: 0,
  on_time: null,
  lines: [
    {
      id: 1,
      order_line: 1,
      article_code: 'PF-PAT-LASBOL-BRE-300',
      article_name: 'Lasagnes bolognaise 300 g',
      unit: 'u',
      lot: 31,
      lot_number: 'LF-261103-0001',
      expiry_date: '2026-11-17',
      location_code: 'PFN-FRAIS-A',
      quantity: '360.000',
      fefo_justification: '',
    },
  ],
  pallets: [],
  summary: [
    {
      order_line: 1,
      article_code: 'PF-PAT-LASBOL-BRE-300',
      article_name: 'Lasagnes bolognaise 300 g',
      ordered: '400.000',
      prepared: '360.000',
      missing: '40.000',
    },
  ],
}

const SHIPPED: ShipmentDetail = {
  ...SHIPMENT,
  status: 'expediee',
  status_label: 'Expédiée',
  carrier: 'Transports Frigo Atlantique',
  loading_temperature: '2.8',
  shipped_at: '2026-11-04T15:00:00Z',
  shipped_by_name: 'paul',
  pallet_count: 1,
  on_time: true,
  pallets: [
    {
      id: 1,
      sscc: '037700000000000016',
      rank: 1,
      total_quantity: '360.000',
      lines: [
        {
          id: 1,
          article_code: 'PF-PAT-LASBOL-BRE-300',
          article_name: 'Lasagnes bolognaise 300 g',
          lot_number: 'LF-261103-0001',
          expiry_date: '2026-11-17',
          quantity: '360.000',
        },
      ],
    },
  ],
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Préparation', () => {
  it('le magasinier peut préparer une commande reçue, pas le commercial', async () => {
    mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/ventes/orders/7/': { body: ORDER },
    })
    const { unmount } = renderApp('/ventes/7')
    expect(await screen.findByRole('link', { name: 'Préparer' })).toHaveAttribute(
      'href',
      '/ventes/7/preparation',
    )
    unmount()

    mockApi({
      '/api/auth/me/': { body: SALES },
      '/api/ventes/orders/7/': { body: ORDER },
    })
    renderApp('/ventes/7')
    expect(await screen.findByRole('button', { name: 'Annuler la commande' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Préparer' })).not.toBeInTheDocument()
  })

  it('pré-remplit les lots en FEFO et demande une justification hors FEFO', async () => {
    const fetchMock = mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/ventes/orders/7/picking-proposal/': { body: PROPOSAL },
      '/api/ventes/orders/7/prepare/': { status: 201, body: SHIPMENT },
      '/api/ventes/orders/7/': { body: ORDER },
      '/api/ventes/shipments/4/': { body: SHIPMENT },
    })
    renderApp('/ventes/7/preparation')
    const user = userEvent.setup()

    const first = await screen.findByLabelText('Préparé LF-261103-0001')
    expect(first).toHaveValue(300)
    expect(screen.getByLabelText('Préparé LF-261104-0001')).toHaveValue(100)
    expect(screen.getByText(/Lots écartés car trop courts pour ENS2/)).toBeInTheDocument()
    expect(screen.queryByLabelText('Justification LF-261104-0001')).not.toBeInTheDocument()

    // On prend moins du premier lot : le second devient hors FEFO, et il y a une rupture
    await user.clear(first)
    await user.type(first, '260')
    expect(screen.getByText('Rupture : 40 u ne seront pas livrés.')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Justification LF-261104-0001'), 'Palette filmée')
    await user.click(screen.getByRole('button', { name: 'Enregistrer la préparation' }))

    expect(await screen.findByText('BL-2026-00004')).toBeInTheDocument()
    const call = fetchMock.mock.calls.find(([url]) => url === '/api/ventes/orders/7/prepare/')
    expect(JSON.parse(call?.[1]?.body as string)).toEqual({
      lines: [
        { order_line: 1, lot: 31, location: 8, quantity: '260', justification: '' },
        { order_line: 1, lot: 32, location: 8, quantity: '100', justification: 'Palette filmée' },
      ],
    })
  })
})

describe('Expédition', () => {
  it('expédie avec le transporteur et la température', async () => {
    const fetchMock = mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/ventes/shipments/4/ship/': { body: SHIPPED },
      '/api/ventes/shipments/4/': { body: SHIPMENT },
    })
    renderApp('/expeditions/4')
    const user = userEvent.setup()

    expect(await screen.findByText('40 u')).toBeInTheDocument() // rupture
    await user.type(screen.getByLabelText('Transporteur'), 'Transports Frigo Atlantique')
    await user.type(screen.getByLabelText('Température au chargement (°C)'), '2.8')
    await user.click(screen.getByRole('button', { name: 'Expédier' }))

    await vi.waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url === '/api/ventes/shipments/4/ship/')
      expect(JSON.parse(call?.[1]?.body as string)).toEqual({
        carrier: 'Transports Frigo Atlantique',
        temperature: '2.8',
      })
    })
  })

  it('affiche les palettes avec leur SSCC', async () => {
    mockApi({
      '/api/auth/me/': { body: SALES },
      '/api/ventes/shipments/4/': { body: SHIPPED },
    })
    renderApp('/expeditions/4')
    expect(await screen.findByText('(00) 0 3770000 000000001 6')).toBeInTheDocument()
    expect(screen.getByText("à l'heure")).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Expédier' })).not.toBeInTheDocument()
  })

  it('signale un refus pour température', async () => {
    mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/ventes/shipments/4/': {
        body: {
          ...SHIPMENT,
          status: 'refusee',
          status_label: 'Refusée (température)',
          refusal_reason: 'Température de 5,8 °C au chargement du BL-2026-00004',
        },
      },
    })
    renderApp('/expeditions/4')
    expect(await screen.findByText(/5,8 °C au chargement/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Expédier' })).not.toBeInTheDocument()
  })

  it('liste les bons de livraison', async () => {
    mockApi({
      '/api/auth/me/': { body: SALES },
      '/api/ventes/shipments/': { body: paginated([SHIPPED]) },
    })
    renderApp('/expeditions')
    expect(await screen.findByRole('link', { name: 'BL-2026-00004' })).toBeInTheDocument()
    expect(screen.getByText("à l'heure")).toBeInTheDocument()
  })
})

describe('Taux de service', () => {
  it('affiche en rouge un taux sous l’objectif', async () => {
    const row = {
      ordered: '300.000',
      on_time: '160.000',
      late: '100.000',
      missing: '40.000',
      orders: 3,
      perfect_orders: 1,
      pending_orders: 0,
      rate: '53.3',
      below_target: true,
    }
    const report: ServiceRate = {
      start: '2026-10-06',
      end: '2026-11-04',
      target: '98.5',
      customers: [{ customer: 2, customer_code: 'ENS2', customer_name: 'Marché Plus', ...row }],
      total: row,
      issues: [
        {
          order: 7,
          order_number: 'CC-2026-00007',
          customer_code: 'ENS2',
          requested_delivery_date: '2026-11-04',
          problem: 'en retard',
          ordered: '100.000',
          delivered: '100.000',
          shipped_at: '2026-11-04T15:00:00Z',
        },
      ],
    }
    mockApi({
      '/api/auth/me/': { body: SALES },
      '/api/ventes/service-rate/': { body: report },
    })
    renderApp('/taux-de-service')

    const badges = await screen.findAllByText('53,3 %')
    expect(badges[0]).toHaveClass('badge-danger')
    expect(screen.getByRole('link', { name: 'CC-2026-00007' })).toBeInTheDocument()
    expect(screen.getByText('en retard')).toBeInTheDocument()
  })
})

describe('Invendables', () => {
  const LOT: LotDetail = {
    id: 31,
    number: 'LF-261103-0003',
    article: 70,
    article_code: 'PF-GRA-GRADAU-BRE-1000',
    article_name: 'Gratin dauphinois 1 kg',
    article_type: 'PF',
    article_temperature_class: 'froid_positif',
    unit: 'u',
    supplier_code: null,
    supplier_lot_number: '',
    reception_date: null,
    production_date: '2026-11-03',
    date_type: 'DLC',
    expiry_date: '2026-11-15',
    is_expired: false,
    initial_quantity: '300.000',
    quantity: '6.000',
    location_code: 'PFN-FRAIS-A',
    site_code: 'PFN',
    status: 'bloque',
    status_label: 'Bloqué',
    block_reason: 'Température de 5,8 °C au chargement',
    reception_number: null,
    created_at: '2026-11-03T07:30:00Z',
    stock_by_location: [
      {
        location: 8,
        location_code: 'PFN-FRAIS-A',
        location_name: 'Stock produits finis',
        site_code: 'PFN',
        quantity: '6.000',
      },
    ],
    status_changes: [],
  }

  it('la qualité sort un produit fini bloqué en invendable', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchMock = mockApi({
      '/api/auth/me/': { body: QUALITY },
      '/api/stocks/lots/31/dispose/': { body: { ...LOT, status: 'detruit' } },
      '/api/stocks/lots/31/': { body: LOT },
      '/api/stocks/movements/': { body: paginated([]) },
      '/api/referentiel/locations/': { body: paginated([]) },
    })
    renderApp('/lots/31')
    const user = userEvent.setup()

    await user.selectOptions(await screen.findByLabelText('Destination'), 'destruction')
    await user.type(screen.getByLabelText('Motif'), 'Chaîne du froid rompue')
    await user.click(screen.getByRole('button', { name: 'Sortir en invendable' }))

    await vi.waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url === '/api/stocks/lots/31/dispose/')
      expect(JSON.parse(call?.[1]?.body as string)).toEqual({
        destination: 'destruction',
        reason: 'Chaîne du froid rompue',
      })
    })
  })

  it('pas de sortie en invendable pour un lot libéré dans sa date', async () => {
    mockApi({
      '/api/auth/me/': { body: QUALITY },
      '/api/stocks/lots/31/': { body: { ...LOT, status: 'libere', block_reason: '' } },
      '/api/stocks/movements/': { body: paginated([]) },
      '/api/referentiel/locations/': { body: paginated([]) },
    })
    renderApp('/lots/31')
    expect(await screen.findByText('Décision qualité')).toBeInTheDocument()
    expect(screen.queryByText('Sortir en invendable')).not.toBeInTheDocument()
  })
})
