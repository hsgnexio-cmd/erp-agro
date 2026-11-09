import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { MasterPlan } from '../api/production'
import { TEST_USER, mockApi, paginated, renderApp } from '../test/utils'

const PRODUCTION = { ...TEST_USER, roles: ['production'] }
const SALES = { ...TEST_USER, roles: ['commercial'] }

const DAYS = ['2026-11-16', '2026-11-17', '2026-11-18', '2026-11-19', '2026-11-20']

function plan(overrides: Partial<MasterPlan> = {}): MasterPlan {
  return {
    id: 3,
    week: '2026-11-16',
    week_label: 'S47',
    status: 'brouillon',
    status_label: 'Brouillon',
    forecast_version: 'PRV-2026-00004',
    computed_at: '2026-11-09T10:00:00Z',
    computed_by_name: 'marc',
    frozen_at: null,
    frozen_by_name: '',
    days: DAYS,
    capacity_hours: '15',
    items: [
      {
        article: 65,
        article_code: 'PF-PAT-LASBOL-BRE-300',
        article_name: 'Lasagnes bolognaise 300 g',
        brand: 'Brévanne',
        line: 1,
        line_code: 'L1',
        forecast_quantity: '7000.000',
        ordered_quantity: '0.000',
        demand: '7000.000',
        safety_days: '1.0',
        safety_stock: '1000.000',
        stock: '1200.000',
        open_orders: '600.000',
        demand_before: '1800.000',
        projected_stock: '0.000',
        proposed_quantity: '8004.000',
        days: DAYS.map((day, index) => ({
          day,
          quantity: index < 2 ? '1608.000' : '1596.000',
          production_order: null,
          production_order_number: null,
          deviation: '',
        })),
      },
    ],
    load: [
      {
        line: 1,
        line_code: 'L1',
        cells: DAYS.map((day, index) => ({ day, hours: index === 0 ? '17.0' : '0.7', overload: index === 0 })),
      },
    ],
    ...overrides,
  }
}

function mockPlan(user = PRODUCTION, detail = plan()) {
  return mockApi({
    '/api/auth/me/': { body: user },
    '/api/production/master-plans/?week=': {
      body: paginated([{ id: 3, week: detail.week, week_label: 'S47', status: detail.status }]),
    },
    '/api/production/master-plans/3/': { body: detail },
    '/api/referentiel/articles/': { body: paginated([]) },
  })
}

describe('Plan de production', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('montre le calcul, la répartition sur 5 jours et la charge des lignes', async () => {
    mockPlan()
    renderApp('/plan-production')
    const row = (await screen.findByText('PF-PAT-LASBOL-BRE-300')).closest('tr')!
    // Calculé et total identiques : rien n'a été ajusté
    expect(within(row).getAllByText('8 004')).toHaveLength(2)
    expect(within(row).getByLabelText('PF-PAT-LASBOL-BRE-300 2026-11-16')).toHaveValue(1608)
    expect(within(row).getByText('0').closest('td')).toHaveAttribute(
      'title',
      expect.stringContaining('OF à venir 600'),
    )
    expect(screen.getByText('17 h')).toHaveClass('badge-danger')
  })

  it('ajuste une quantité en quittant la case', async () => {
    const fetchMock = mockPlan()
    renderApp('/plan-production')
    const input = await screen.findByLabelText('PF-PAT-LASBOL-BRE-300 2026-11-16')
    await userEvent.clear(input)
    await userEvent.type(input, '2400')
    await userEvent.tab()
    const call = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/3/set-quantity/'))
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({
      article: 65,
      day: '2026-11-16',
      quantity: '2400',
    })
  })

  it('demande une confirmation avant de figer', async () => {
    const fetchMock = mockPlan()
    renderApp('/plan-production')
    await userEvent.click(await screen.findByRole('button', { name: 'Figer le plan' }))
    const group = screen.getByRole('group', { name: 'Confirmer le gel' })
    expect(group).toHaveTextContent('Un OF planifié sera créé')
    await userEvent.click(within(group).getByRole('button', { name: 'Confirmer le gel' }))
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/3/freeze/'))).toBe(true)
  })

  it('un plan figé affiche les OF et les écarts, sans saisie', async () => {
    const frozen = plan({ status: 'fige', status_label: 'Figé', frozen_at: '2026-11-14T11:00:00Z' })
    frozen.items[0].days[0] = {
      ...frozen.items[0].days[0],
      production_order: 40,
      production_order_number: 'OF-2026-00040',
      deviation: 'quantité 1200',
    }
    mockPlan(PRODUCTION, frozen)
    renderApp('/plan-production')
    expect(await screen.findByRole('link', { name: 'OF-2026-00040' })).toHaveAttribute('href', '/production/40')
    expect(screen.getByText('quantité 1200')).toHaveClass('badge-warn')
    expect(screen.getByText(/figé le .* \(automatique\)/)).toBeInTheDocument()
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Figer le plan' })).not.toBeInTheDocument()
  })

  it('le commercial consulte sans pouvoir modifier', async () => {
    mockPlan(SALES)
    renderApp('/plan-production')
    await screen.findByText('PF-PAT-LASBOL-BRE-300')
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Recalculer' })).not.toBeInTheDocument()
  })

  it('propose de calculer quand la semaine n’a pas encore de plan', async () => {
    mockApi({
      '/api/auth/me/': { body: PRODUCTION },
      '/api/production/master-plans/?week=': { body: paginated([]) },
    })
    renderApp('/plan-production')
    expect(await screen.findByText('Aucun plan pour cette semaine.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Calculer le plan' })).toBeInTheDocument()
  })
})
