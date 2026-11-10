import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Planning, ProductionOrderDetail, ProposalRow } from '../api/production'
import { TEST_USER, mockApi, renderApp } from '../test/utils'

const PRODUCTION = { ...TEST_USER, roles: ['production'] }
const QUALITY = { ...TEST_USER, roles: ['qualite'] }

const ORDER: ProductionOrderDetail = {
  id: 3,
  number: 'OF-2026-00003',
  article: 61,
  article_code: 'SF-BECHAMEL',
  article_name: 'Sauce béchamel à la crème',
  article_type: 'SF',
  unit: 'kg',
  planned_quantity: '100.000',
  planned_date: '2026-11-04',
  sequence: 1,
  site: 1,
  site_code: 'NAN',
  line: null,
  line_code: null,
  output_location_code: 'NAN-CF-SF',
  status: 'lance',
  status_label: 'Lancé',
  comment: '',
  produced_quantity: '0',
  mass_yield: null,
  needs: [
    {
      component: 20,
      component_code: 'MP-LAI-CREME35',
      component_name: 'Crème',
      unit: 'kg',
      net: '10.000',
      gross: '10.000',
    },
  ],
  declarations: [],
  yield_report: { produced: '0', mass_yield: null, below_target: false, target: '96', components: [] },
  allergens: ['Lait'],
  created_by_name: 'paul',
  launched_at: '2026-11-04T07:00:00Z',
  closed_at: null,
}

const PROPOSAL: ProposalRow[] = [
  {
    component: 20,
    component_code: 'MP-LAI-CREME35',
    component_name: 'Crème',
    unit: 'kg',
    need: '10.000',
    missing: '0',
    lots: [
      {
        lot: 1,
        lot_number: 'LR-261025-0001',
        expiry_date: '2026-11-13',
        location: 6,
        location_code: 'NAN-CF-MP',
        available: '90.000',
        suggested: '10.000',
      },
      {
        lot: 2,
        lot_number: 'LR-261101-0001',
        expiry_date: '2026-11-21',
        location: 6,
        location_code: 'NAN-CF-MP',
        available: '60.000',
        suggested: '0',
      },
    ],
  },
]

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Ordre de fabrication', () => {
  it('la production voit « Déclarer » sur un OF lancé, la qualité non', async () => {
    mockApi({
      '/api/auth/me/': { body: QUALITY },
      '/api/production/orders/3/': { body: ORDER },
    })
    renderApp('/production/3')
    expect(await screen.findByText('MP-LAI-CREME35')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Déclarer une production' })).not.toBeInTheDocument()
  })

  it('affiche le rendement et le signale sous l’objectif', async () => {
    mockApi({
      '/api/auth/me/': { body: PRODUCTION },
      '/api/production/orders/3/': {
        body: {
          ...ORDER,
          status: 'termine',
          status_label: 'Terminé',
          produced_quantity: '100',
          declarations: [
            {
              id: 1,
              lot: 9,
              lot_number: 'LF-261104-0001',
              quantity: '100.000',
              declared_at: '2026-11-04T10:00:00Z',
              user_name: 'paul',
              comment: '',
              fefo_deviations: [],
            },
          ],
          yield_report: {
            produced: '100',
            mass_yield: '94.9',
            below_target: true,
            target: '96',
            components: [
              {
                component_code: 'MP-LAI-CREME35',
                unit: 'kg',
                theoretical: '10.000',
                actual: '10.600',
                gap_pct: '6.0',
              },
            ],
          },
        },
      },
    })
    renderApp('/production/3')
    expect(await screen.findByText('94,9 % (objectif 96 %)')).toHaveClass('badge-danger')
    expect(screen.getByText('+6 %')).toBeInTheDocument()
  })
})

describe('Déclaration de production', () => {
  it('pré-remplit le FEFO et demande une justification pour un autre lot', async () => {
    const fetchMock = mockApi({
      '/api/auth/me/': { body: PRODUCTION },
      '/api/production/orders/3/proposal/': { body: PROPOSAL },
      '/api/production/orders/3/declare/': { status: 201, body: {} },
      '/api/production/orders/3/': { body: ORDER },
    })
    renderApp('/production/3/declaration')
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Quantité produite (kg)'), '100')
    await user.click(screen.getByRole('button', { name: 'Proposer les lots (FEFO)' }))

    const first = await screen.findByLabelText('Consommé LR-261025-0001')
    expect(first).toHaveValue(10)
    expect(screen.queryByLabelText('Justification LR-261101-0001')).not.toBeInTheDocument()

    // On prend le second lot à la place du premier : hors FEFO
    await user.clear(first)
    await user.type(first, '0')
    const second = screen.getByLabelText('Consommé LR-261101-0001')
    await user.clear(second)
    await user.type(second, '10')
    await user.type(
      await screen.findByLabelText('Justification LR-261101-0001'),
      'Lot introuvable en chambre froide',
    )
    await user.click(screen.getByRole('button', { name: /Enregistrer la déclaration/ }))

    await vi.waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url === '/api/production/orders/3/declare/')
      expect(JSON.parse(call?.[1]?.body as string)).toEqual({
        quantity: '100',
        comment: '',
        consumptions: [
          {
            lot: 2,
            location: 6,
            quantity: '10',
            justification: 'Lot introuvable en chambre froide',
          },
        ],
      })
    })
  })
})

describe('Planning', () => {
  it('affiche la charge et les avertissements', async () => {
    const planning: Planning = {
      week_start: '2026-11-02',
      days: ['2026-11-02', '2026-11-03', '2026-11-04', '2026-11-05', '2026-11-06', '2026-11-07', '2026-11-08'],
      capacity_hours: '15',
      lines: [
        {
          line: 1,
          line_code: 'L1',
          line_name: 'Pâtes 300 g',
          site_code: 'NAN',
          capacity_per_hour: 2400,
          cells: [
            {
              date: '2026-11-02',
              closed: '',
              hours: '16.0',
              warnings: ['Surcharge : 16.0 h prévues pour 15 h disponibles.'],
              orders: [
                {
                  id: 4,
                  number: 'OF-2026-00004',
                  article_code: 'PF-PAT-LASBOL-ENS1-300',
                  quantity: '38400',
                  status: 'planifie',
                  status_label: 'Planifié',
                  sequence: 1,
                  hours: '16.0',
                  allergens: ['Lait'],
                },
              ],
            },
            ...['03', '04', '05', '06', '07', '08'].map((day) => ({
              date: `2026-11-${day}`,
              closed: ['07', '08'].includes(day) ? 'week-end' : '',
              hours: '0',
              warnings: [],
              orders: [],
            })),
          ],
        },
      ],
    }
    mockApi({
      '/api/auth/me/': { body: PRODUCTION },
      '/api/production/planning/': { body: planning },
    })
    renderApp('/planning')

    expect(await screen.findByRole('link', { name: 'OF-2026-00004' })).toBeInTheDocument()
    expect(screen.getByText('Charge : 16 h')).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent('Surcharge')
  })
})
