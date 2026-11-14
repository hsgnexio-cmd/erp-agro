import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mrp, MrpProposal } from '../api/mrp'
import { TEST_USER, mockApi, renderApp } from '../test/utils'

const BUYER = { ...TEST_USER, roles: ['acheteur'] }
const STOREKEEPER = { ...TEST_USER, roles: ['magasinier'] }

function proposal(overrides: Partial<MrpProposal>): MrpProposal {
  return {
    article: 10,
    article_code: 'EM-BARQ-300N',
    article_name: 'Barquette 300 g noire',
    article_type: 'EM',
    unit: 'u',
    supplier: 13,
    supplier_code: 'FOU-013',
    supplier_name: 'Emballages de l’Ouest',
    lead_time_days: 35,
    week: '2026-11-16',
    week_label: 'S47',
    need_date: '2026-11-16',
    order_date: '2026-10-12',
    late: true,
    net: '35924.000',
    quantity: '35924.000',
    min_order_quantity: '5000.000',
    raised_to_minimum: false,
    unit_price: '0.0800',
    amount: '2873.92',
    ...overrides,
  }
}

const MRP: Mrp = {
  computed_at: '2026-11-09T10:00:00Z',
  weeks: [
    { week: '2026-11-09', label: 'S46', source: 'OF de la semaine' },
    { week: '2026-11-16', label: 'S47', source: 'plan brouillon' },
  ],
  proposals: [
    proposal({}),
    proposal({
      article: 20, article_code: 'MP-LAI-CREME35', article_name: 'Crème 35 %', article_type: 'MP',
      unit: 'kg', supplier: 5, supplier_code: 'FOU-005', supplier_name: 'Crèmerie',
      lead_time_days: 3, order_date: '2099-01-01', late: false, net: '50.000',
      quantity: '500.000', raised_to_minimum: true, unit_price: '4.2000', amount: '2100.00',
    }),
  ],
  articles: [
    {
      article: 10,
      article_code: 'EM-BARQ-300N',
      article_name: 'Barquette 300 g noire',
      unit: 'u',
      stock: '1000.000',
      weeks: [
        { week: '2026-11-09', gross: '0', receipts: '0', planned: '0', projected: '1000' },
        { week: '2026-11-16', gross: '36924', receipts: '0', planned: '35924', projected: '0' },
      ],
    },
  ],
}

function mockMrp(user = BUYER) {
  return mockApi({
    '/api/auth/me/': { body: user },
    '/api/achats/mrp/?v=': { body: MRP },
    '/api/achats/mrp/create-orders/': {
      status: 201,
      body: [{ id: 31, number: 'CA-2026-00031', supplier_code: 'FOU-013', expected_delivery_date: '2026-12-14', line_count: 1 }],
    },
  })
}

describe("Besoins d'achat", () => {
  afterEach(() => vi.unstubAllGlobals())

  it('montre les propositions à passer maintenant, les retards en rouge', async () => {
    mockMrp()
    renderApp('/besoins-achat')
    const table = await screen.findByRole('table', { name: "Propositions d'achat" })
    const row = within(table).getByText('EM-BARQ-300N').closest('tr')!
    expect(within(row).getByText('en retard')).toHaveClass('badge-danger')
    // La crème est à commander en 2099 : hors de l'horizon « 7 jours » par défaut
    expect(within(table).queryByText('MP-LAI-CREME35')).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Horizon'), 'all')
    expect(within(table).getByText('MP-LAI-CREME35').closest('tr')!).toHaveTextContent('minimum')
    expect(screen.getByText('plan brouillon')).toBeInTheDocument()
  })

  it('crée les commandes brouillon des propositions choisies', async () => {
    const fetchMock = mockMrp()
    renderApp('/besoins-achat')
    await userEvent.click(await screen.findByLabelText('Sélectionner EM-BARQ-300N S47'))
    const quantity = screen.getByLabelText('Quantité EM-BARQ-300N S47')
    await userEvent.clear(quantity)
    await userEvent.type(quantity, '40000')
    await userEvent.click(screen.getByRole('button', { name: 'Créer les commandes brouillon (1)' }))

    const call = fetchMock.mock.calls.find(([url]) => String(url) === '/api/achats/mrp/create-orders/')
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({
      selections: [{ article: 10, week: '2026-11-16', quantity: '40000' }],
    })
    expect(await screen.findByRole('link', { name: 'CA-2026-00031' })).toHaveAttribute('href', '/commandes/31')
  })

  it('génère la commande d’une seule proposition, sans passer par les cases à cocher', async () => {
    const fetchMock = mockMrp()
    renderApp('/besoins-achat')
    const summary = await screen.findByLabelText('Synthèse des besoins')
    expect(within(summary).getByText('en retard : rupture probable')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Générer la commande EM-BARQ-300N S47' }))

    const call = fetchMock.mock.calls.find(([url]) => String(url) === '/api/achats/mrp/create-orders/')
    const body = JSON.parse(String(call?.[1]?.body))
    expect(body.selections).toHaveLength(1)
    expect(body.selections[0]).toMatchObject({ article: 10, week: '2026-11-16' })
    expect(await screen.findByRole('link', { name: 'CA-2026-00031' })).toBeInTheDocument()
  })

  it('affiche le calcul semaine par semaine d’un article', async () => {
    mockMrp()
    renderApp('/besoins-achat')
    await userEvent.click(await screen.findByRole('button', { name: 'EM-BARQ-300N' }))
    const detail = screen.getByRole('table', { name: 'Détail du calcul EM-BARQ-300N' })
    expect(within(detail).getByText('36 924')).toBeInTheDocument()
    expect(within(detail).getByText(/stock disponible 1 000/)).toBeInTheDocument()
  })

  it('le magasinier consulte sans pouvoir commander', async () => {
    mockMrp(STOREKEEPER)
    renderApp('/besoins-achat')
    await screen.findByText('EM-BARQ-300N')
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Créer les commandes/ })).not.toBeInTheDocument()
  })
})
