import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { RecallImpact, TraceNode } from '../api/quality'
import { TEST_USER, mockApi, renderApp } from '../test/utils'

const QUALITY = { ...TEST_USER, roles: ['qualite'] }
const STOREKEEPER = { ...TEST_USER, roles: ['magasinier'] }

function node(lot: number, number: string, article: string, extra: Partial<TraceNode> = {}) {
  return {
    lot,
    lot_number: number,
    article_code: article,
    article_name: article,
    article_type: article.slice(0, 2),
    unit: article.startsWith('PF') ? 'u' : 'kg',
    status: 'libere',
    status_label: 'Libéré',
    expiry_date: '2026-11-17',
    quantity: null,
    shipments: [],
    children: [],
    ...extra,
  } satisfies TraceNode
}

const CREAM = 'LR-261025-0001'

const TRACE = {
  upstream: node(1, CREAM, 'MP-LAI-CREME35'),
  downstream: node(1, CREAM, 'MP-LAI-CREME35', {
    children: [
      node(2, 'LF-261102-0001', 'SF-BECHAMEL', {
        quantity: '60.000',
        children: [
          node(3, 'LF-261103-0001', 'PF-PAT-LASBOL-BRE-300', {
            quantity: '90.000',
            shipments: [
              {
                customer_code: 'ENS1',
                warehouse_code: 'ENS1-E01',
                warehouse_name: 'Entrepôt Hyper Atlantique Rennes',
                quantity: '400.000',
                last_shipped: '2026-11-04T10:00:00Z',
              },
            ],
          }),
        ],
      }),
    ],
  }),
}

const IMPACT: RecallImpact = {
  origin: {
    id: 1,
    number: CREAM,
    article_code: 'MP-LAI-CREME35',
    article_name: 'Crème',
    article_type: 'MP',
    unit: 'kg',
    status: 'libere',
    status_label: 'Libéré',
    expiry_date: '2026-11-13',
  },
  computed_at: '2026-11-04T11:00:00Z',
  lots: [
    {
      id: 3,
      number: 'LF-261103-0001',
      article_code: 'PF-PAT-LASBOL-BRE-300',
      article_name: 'Lasagnes bolognaise 300 g',
      article_type: 'PF',
      unit: 'u',
      status: 'libere',
      status_label: 'Libéré',
      expiry_date: '2026-11-17',
      level: 2,
      stock_total: '150.000',
      stock: [{ location_code: 'PFN-FRAIS-A', site_code: 'PFN', quantity: '150.000' }],
    },
  ],
  deliveries: [
    {
      lot_number: 'LF-261103-0001',
      article_code: 'PF-PAT-LASBOL-BRE-300',
      article_name: 'Lasagnes',
      unit: 'u',
      expiry_date: '2026-11-17',
      customer_code: 'ENS1',
      customer_name: 'Hyper Atlantique',
      warehouse_code: 'ENS1-E01',
      warehouse_name: 'Entrepôt Hyper Atlantique Rennes',
      city: 'Rennes',
      quantity: '400.000',
      last_shipped: '2026-11-04T10:00:00Z',
    },
  ],
  customers: [{ code: 'ENS1', name: 'Hyper Atlantique', deliveries: 1, quantities: { u: '400' } }],
  lots_to_block: ['LF-261103-0001'],
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Traçabilité', () => {
  it("montre l'aval d'un lot de crème jusqu'aux enseignes livrées", async () => {
    mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/qualite/traceability/': { body: TRACE },
    })
    renderApp(`/tracabilite?lot=${CREAM}`)

    expect(await screen.findByRole('link', { name: 'LF-261103-0001' })).toBeInTheDocument()
    expect(screen.getByText(/ENS1 – Entrepôt Hyper Atlantique Rennes : 400 u/)).toBeInTheDocument()
    expect(screen.getByText(/Lot reçu d'un fournisseur/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Simuler un rappel de ce lot' })).toHaveAttribute(
      'href',
      `/rappels/simulation?lot=${CREAM}`,
    )
  })
})

describe('Rappel', () => {
  it('la qualité voit l’impact puis lance le rappel avec un motif', async () => {
    vi.stubGlobal('confirm', () => true)
    const fetchMock = mockApi({
      '/api/auth/me/': { body: QUALITY },
      '/api/qualite/recall-simulation/': { body: IMPACT },
      '/api/qualite/recalls/': {
        status: 201,
        body: {
          id: 4,
          number: 'RAP-2026-00001',
          origin_lot: 1,
          origin_lot_number: CREAM,
          origin_article_code: 'MP-LAI-CREME35',
          reason: 'Listeria',
          created_at: '2026-11-04T11:05:00Z',
          created_by_name: 'claire',
          blocked_lot_count: 1,
          snapshot: { ...IMPACT, blocked_lots: ['LF-261103-0001'] },
        },
      },
    })
    renderApp(`/rappels/simulation?lot=${CREAM}`)
    const user = userEvent.setup()

    expect(await screen.findByText('150 u en PFN-FRAIS-A')).toBeInTheDocument()
    expect(screen.getByText('ENS1 – Hyper Atlantique')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Motif du rappel (obligatoire)'), 'Listeria')
    await user.click(screen.getByRole('button', { name: 'Lancer le rappel' }))

    expect(await screen.findByRole('heading', { name: /Rappel RAP-2026-00001/ })).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /Télécharger la liste des clients à prévenir/ }),
    ).toHaveAttribute('href', '/api/qualite/recalls/4/export/')
    const call = fetchMock.mock.calls.find(([url]) => url === '/api/qualite/recalls/')
    expect(JSON.parse(call?.[1]?.body as string)).toEqual({ lot_number: CREAM, reason: 'Listeria' })
  })

  it("un magasinier peut simuler mais pas lancer le rappel", async () => {
    mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/qualite/recall-simulation/': { body: IMPACT },
    })
    renderApp(`/rappels/simulation?lot=${CREAM}`)

    expect(await screen.findByText('ENS1 – Hyper Atlantique')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Lancer le rappel' })).not.toBeInTheDocument()
  })
})
