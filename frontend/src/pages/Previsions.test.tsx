import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Accuracy, Forecast, Promotion } from '../api/forecast'
import { TEST_USER, mockApi, paginated, renderApp } from '../test/utils'

const SALES = { ...TEST_USER, roles: ['commercial'] }
const PRODUCTION = { ...TEST_USER, roles: ['production'] }

const WEEKS = [
  { week: '2026-11-09', label: 'S46' },
  { week: '2026-11-16', label: 'S47' },
]

const FORECAST: Forecast = {
  computed_at: '2026-11-07T10:00:00Z',
  current_week: '2026-11-02',
  weeks: WEEKS,
  rows: [
    {
      customer: 2,
      customer_code: 'ENS2',
      article: 65,
      article_code: 'PF-PAT-LASBOL-BRE-300',
      article_name: 'Lasagnes bolognaise 300 g',
      cells: [
        {
          week: '2026-11-09',
          base: '1200',
          promotion: null,
          promo_coefficient: null,
          promo_quantity: null,
          adjustment: null,
          quantity: '1200',
        },
        {
          week: '2026-11-16',
          base: '1200',
          promotion: 4,
          promo_coefficient: '2.50',
          promo_quantity: '3000',
          adjustment: {
            id: 9,
            quantity: '2400.000',
            reason: 'Stock magasin déjà constitué',
            created_at: '2026-11-06T09:00:00Z',
            created_by_name: 'paul',
          },
          quantity: '2400.000',
        },
      ],
    },
  ],
}

const PROMOTION: Promotion = {
  id: 4,
  customer: 2,
  customer_code: 'ENS2',
  article: 65,
  article_code: 'PF-PAT-LASBOL-BRE-300',
  article_name: 'Lasagnes bolognaise 300 g',
  first_week: '2026-11-16',
  first_week_label: 'S47',
  last_week: '2026-11-16',
  last_week_label: 'S47',
  coefficient: '2.50',
  announced_on: '2026-11-02',
  notice_days: 14,
  late_notice: true,
  comment: '',
  created_at: '2026-11-02T10:00:00Z',
  created_by_name: 'paul',
  cancelled_at: null,
  cancelled_by_name: '',
  cancel_reason: '',
}

const ACCURACY: Accuracy = {
  start: '2026-09-13',
  end: '2026-11-07',
  target: '80',
  accuracy: '83.4',
  weeks: [
    {
      week: '2026-10-19', label: 'S43', version_number: 'PRV-2026-00002',
      version_created_at: '2026-10-12T03:00:00Z', forecast: '9000', actual: '9500',
      abs_error: '1100', accuracy: '88.4', complete: true,
    },
    {
      week: '2026-10-26', label: 'S44', version_number: 'PRV-2026-00003',
      version_created_at: '2026-10-19T03:00:00Z', forecast: '9000', actual: '8000',
      abs_error: '2100', accuracy: '73.8', complete: true,
    },
    {
      week: '2026-11-02', label: 'S45', version_number: 'PRV-2026-00004',
      version_created_at: '2026-10-26T04:00:00Z', forecast: '9000', actual: '5000',
      abs_error: '4000', accuracy: '20.0', complete: false,
    },
  ],
}

function mockForecast(user = SALES) {
  return mockApi({
    '/api/auth/me/': { body: user },
    '/api/referentiel/customers/': {
      body: paginated([{ id: 2, code: 'ENS2', name: 'Marché Plus' }]),
    },
    '/api/previsions/forecast/': { body: FORECAST },
    '/api/previsions/promotions/': { body: paginated([PROMOTION]) },
    '/api/previsions/accuracy/': { body: ACCURACY },
    '/api/previsions/versions/': { body: paginated([]) },
    '/api/previsions/adjustments/': { status: 201, body: {} },
  })
}

describe('Prévisions de vente', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('montre la prévision sur 8 semaines avec promotions et corrections', async () => {
    mockForecast()
    renderApp('/previsions')

    const header = await screen.findByRole('columnheader', { name: /S46/ })
    const grid = header.closest('table')!
    expect(within(grid).getByRole('columnheader', { name: /S47/ })).toBeInTheDocument()
    const row = within(grid).getByText('PF-PAT-LASBOL-BRE-300').closest('tr')!
    const cells = within(row).getAllByRole('cell')
    // Colonnes : enseigne, produit, S46, S47
    expect(cells[2]).toHaveTextContent('1 200')
    expect(cells[3]).toHaveTextContent('2 400 ×2,5 ✎')
    expect(cells[3]).toHaveClass('is-promo', 'is-adjusted')
    expect(cells[3]).toHaveAttribute('title', expect.stringContaining('Stock magasin déjà constitué'))
  })

  it('le commercial corrige une quantité avec un motif', async () => {
    const fetchMock = mockForecast()
    renderApp('/previsions')

    await userEvent.click(await screen.findByRole('button', { name: /ENS2 PF-PAT-LASBOL-BRE-300 2026-11-09/ }))
    const form = screen.getByRole('form', { name: 'Correction de la prévision' })
    const quantity = within(form).getByLabelText('Quantité prévue (unités)')
    expect(quantity).toHaveValue(1200)
    await userEvent.clear(quantity)
    await userEvent.type(quantity, '1560')
    await userEvent.type(within(form).getByLabelText('Motif'), 'Ouverture de 3 magasins')
    await userEvent.click(within(form).getByRole('button', { name: 'Enregistrer la correction' }))

    const call = fetchMock.mock.calls.find(
      ([input, init]) => String(input) === '/api/previsions/adjustments/' && init?.method === 'POST',
    )
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({
      customer: 2,
      article: 65,
      week: '2026-11-09',
      quantity: '1560',
      reason: 'Ouverture de 3 magasins',
    })
  })

  it('signale une promotion annoncée tard', async () => {
    mockForecast()
    renderApp('/previsions')
    expect(await screen.findByText('annoncée tard (14 j avant)')).toHaveClass('badge-warn')
    expect(screen.getByText('Prévue')).toHaveClass('badge-info')
  })

  it('affiche la fiabilité à S-1, la semaine en cours non comptée', async () => {
    mockForecast()
    renderApp('/previsions')
    expect(await screen.findByText('88,4 %')).toHaveClass('badge-ok')
    expect(screen.getByText('73,8 %')).toHaveClass('badge-danger')
    expect(screen.getByText('en cours')).toBeInTheDocument()
    expect(screen.getByText('83,4 %')).toBeInTheDocument()
  })

  it('la production consulte sans pouvoir modifier', async () => {
    mockForecast(PRODUCTION)
    renderApp('/previsions')
    await screen.findByText('PF-PAT-LASBOL-BRE-300')
    expect(screen.queryByRole('button', { name: /ENS2 PF-PAT/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'Nouvelle promotion' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Figer une version' })).not.toBeInTheDocument()
  })
})
