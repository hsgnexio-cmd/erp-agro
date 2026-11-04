import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { CustomerOrderDetail, EdiMessage } from '../api/sales'
import { TEST_USER, mockApi, paginated, renderApp } from '../test/utils'

const SALES = { ...TEST_USER, roles: ['commercial'] }
const STOREKEEPER = { ...TEST_USER, roles: ['magasinier'] }

const ORDER: CustomerOrderDetail = {
  id: 7,
  number: 'CC-2026-00007',
  customer: 2,
  customer_code: 'ENS2',
  customer_name: 'Marché Plus',
  warehouse: 5,
  warehouse_code: 'ENS2-E01',
  warehouse_name: 'Entrepôt Marché Plus Nantes',
  customer_reference: 'MP-458812',
  received_at: '2026-11-04T08:30:00Z',
  requested_delivery_date: '2026-11-05',
  status: 'recue',
  status_label: 'Reçue',
  source: 'edi',
  source_label: 'EDI',
  total_amount: '1032.00',
  line_count: 2,
  to_be_priced: true,
  comment: '',
  lines: [
    {
      id: 1,
      article: 65,
      article_code: 'PF-PAT-LASBOL-BRE-300',
      article_name: 'Lasagnes bolognaise 300 g',
      quantity: '480.000',
      unit_price: '2.1500',
      amount: '1032.00',
      to_be_priced: false,
      shipped_quantity: null,
    },
    {
      id: 2,
      article: 66,
      article_code: 'PF-PAT-COQJAM-BRE-300',
      article_name: 'Gratin de coquillettes',
      quantity: '120.000',
      unit_price: null,
      amount: null,
      to_be_priced: true,
      shipped_quantity: null,
    },
  ],
  edi_message_id: 'ENS2-20261104-001',
  created_by_name: null,
  shipments: [],
}

const REJECTED: EdiMessage = {
  id: 3,
  message_id: 'ENS4-20261104-ERR',
  customer_code: 'ENS4',
  received_at: '2026-11-04T08:55:00Z',
  status: 'rejete',
  status_label: 'Rejeté',
  errors: ['PF-PAT-LASBOL-ENS1-300 est un produit MDD de ENS1.'],
  payload: { message_id: 'ENS4-20261104-ERR' },
  order: null,
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Commandes clients', () => {
  it('signale une ligne sans tarif « à valoriser »', async () => {
    mockApi({
      '/api/auth/me/': { body: SALES },
      '/api/ventes/orders/7/': { body: ORDER },
    })
    renderApp('/ventes/7')

    expect(await screen.findByText('480 u')).toBeInTheDocument()
    expect(screen.getByText('à valoriser')).toBeInTheDocument()
    expect(screen.getByText(/message ENS2-20261104-001/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Annuler la commande' })).toBeInTheDocument()
  })

  it('saisit une commande à partir des produits commandables', async () => {
    const fetchMock = mockApi({
      '/api/auth/me/': { body: SALES },
      '/api/referentiel/customers/': {
        body: paginated([{ id: 2, code: 'ENS2', name: 'Marché Plus' }]),
      },
      '/api/referentiel/customer-warehouses/': {
        body: paginated([{ id: 5, code: 'ENS2-E01', name: 'Entrepôt Nantes', city: 'Nantes' }]),
      },
      '/api/ventes/orderable-articles/': {
        body: {
          earliest_delivery_date: '2026-11-05',
          articles: [
            {
              article: 65,
              article_code: 'PF-PAT-LASBOL-BRE-300',
              article_name: 'Lasagnes',
              unit_price: '2.1500',
            },
          ],
        },
      },
      '/api/ventes/orders/': { status: 201, body: ORDER },
    })
    renderApp('/ventes/nouvelle')
    const user = userEvent.setup()

    await user.selectOptions(
      await screen.findByLabelText('Enseigne'),
      await screen.findByRole('option', { name: 'ENS2 – Marché Plus' }),
    )
    await user.selectOptions(
      await screen.findByLabelText('Entrepôt livré'),
      await screen.findByRole('option', { name: 'ENS2-E01 – Entrepôt Nantes' }),
    )
    await user.type(await screen.findByLabelText('Quantité PF-PAT-LASBOL-BRE-300'), '240')
    await user.click(screen.getByRole('button', { name: 'Enregistrer la commande' }))

    await vi.waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) => url === '/api/ventes/orders/' && init?.method === 'POST',
      )
      expect(JSON.parse(call?.[1]?.body as string)).toEqual({
        customer: 2,
        warehouse: 5,
        requested_delivery_date: '2026-11-05',
        customer_reference: '',
        comment: '',
        lines: [{ article: 65, quantity: '240' }],
      })
    })
  })
})

describe('EDI', () => {
  it('affiche les motifs de rejet et simule les commandes du jour', async () => {
    const fetchMock = mockApi({
      '/api/auth/me/': { body: SALES },
      '/api/ventes/edi-messages/simulate/': { status: 201, body: [REJECTED] },
      '/api/ventes/edi-messages/': { body: paginated([REJECTED]) },
    })
    renderApp('/edi')
    const user = userEvent.setup()

    expect(await screen.findByText(/produit MDD de ENS1/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Simuler les commandes du jour' }))
    expect(await screen.findByText('1 message(s) reçu(s), dont 1 rejeté(s).')).toBeInTheDocument()
    expect(
      fetchMock.mock.calls.some(([url]) => url === '/api/ventes/edi-messages/simulate/'),
    ).toBe(true)
  })

  it('le magasinier consulte sans pouvoir simuler', async () => {
    mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/ventes/edi-messages/': { body: paginated([REJECTED]) },
    })
    renderApp('/edi')
    expect(await screen.findByText('ENS4-20261104-ERR')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Simuler les commandes du jour' }),
    ).not.toBeInTheDocument()
  })
})
