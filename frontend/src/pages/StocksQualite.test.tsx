import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TEST_USER, mockApi, paginated, renderApp } from '../test/utils'

const lot = (overrides: object) => ({
  id: 9,
  number: 'LR-261025-0001',
  article: 20,
  article_code: 'MP-LAI-CREME35',
  article_name: 'Crème fraîche 35 % MG',
  article_type: 'MP',
  article_temperature_class: 'froid_positif',
  unit: 'kg',
  supplier_code: 'FOU-004',
  supplier_lot_number: 'CB-0412',
  reception_date: '2026-10-25',
  date_type: 'DLC',
  expiry_date: '2026-11-13',
  is_expired: false,
  initial_quantity: '400.000',
  quantity: '400.000',
  location_code: 'MPE-FP-01',
  site_code: 'MPE',
  status: 'libere',
  status_label: 'Libéré',
  block_reason: '',
  reception_number: 'REC-2026-00001',
  created_at: '2026-10-25T07:30:00Z',
  ...overrides,
})

const node = (overrides: object) => ({
  lot: 9,
  lot_number: 'LR-261025-0001',
  article_code: 'MP-LAI-CREME35',
  article_name: 'Crème fraîche 35 % MG',
  article_type: 'MP',
  unit: 'kg',
  status: 'libere',
  status_label: 'Libéré',
  expiry_date: '2026-11-13',
  quantity: null,
  shipments: [],
  children: [],
  ...overrides,
})

const reading = (id: number, temperature: string, compliant = true) => ({
  id,
  location: 3,
  location_code: 'MPE-FP-01',
  location_name: 'Chambre froide matières',
  site_code: 'MPE',
  temperature,
  measured_at: `2026-11-0${id}T09:00:00Z`,
  min_allowed: '0.0',
  max_allowed: '4.0',
  is_compliant: compliant,
  user_name: 'marc',
  comment: '',
})

const alert = (id: number, level: string) => ({
  id,
  alert_type: 'peremption',
  alert_type_label: 'Péremption proche',
  level,
  level_label: level === 'critique' ? 'Critique' : 'Attention',
  message: `Alerte ${id}`,
  lot: null,
  lot_number: null,
  location: null,
  location_code: null,
  created_at: '2026-11-04T06:00:00Z',
  is_open: true,
  resolved_at: null,
  resolved_by_name: null,
  resolution_comment: '',
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('Lots', () => {
  it('ouvre la fiche du lot dans un tiroir, avec sa traçabilité et le rappel', async () => {
    mockApi({
      '/api/auth/me/': { body: TEST_USER },
      '/api/stocks/lots/': {
        body: paginated([lot({}), lot({ id: 10, number: 'LR-261020-0003', quantity: '80.000' })]),
      },
      '/api/qualite/traceability/': {
        body: {
          upstream: node({}),
          downstream: node({
            children: [
              node({
                lot: 30,
                lot_number: 'LF-261103-0001',
                article_code: 'PF-GRA-GRADAU-BRE-1000',
                article_name: 'Gratin dauphinois',
                quantity: '62.150',
              }),
            ],
          }),
        },
      },
    })
    renderApp('/lots')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'LR-261025-0001' }))
    const drawer = screen.getByRole('dialog', { name: 'Lot LR-261025-0001' })
    expect(within(drawer).getByText(/lot fournisseur CB-0412/)).toBeInTheDocument()
    expect(within(drawer).getByRole('link', { name: /Fiche complète/ })).toHaveAttribute('href', '/lots/9')
    expect(within(drawer).getByRole('link', { name: /Simuler un rappel de ce lot/ })).toHaveAttribute(
      'href',
      '/rappels/simulation?lot=LR-261025-0001',
    )

    await user.click(within(drawer).getByRole('tab', { name: 'Traçabilité' }))
    expect(await within(drawer).findByRole('link', { name: 'LF-261103-0001' })).toBeInTheDocument()
    expect(within(drawer).getByText(/Lot reçu d'un fournisseur/)).toBeInTheDocument()

    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('trie les lots et propose une action sur la sélection', async () => {
    mockApi({
      '/api/auth/me/': { body: TEST_USER },
      '/api/stocks/lots/': {
        body: paginated([lot({}), lot({ id: 10, number: 'LR-261020-0003', quantity: '80.000' })]),
      },
    })
    renderApp('/lots')
    const user = userEvent.setup()
    await screen.findByRole('button', { name: 'LR-261025-0001' })

    await user.click(screen.getByRole('button', { name: /Quantité/ }))
    const numbers = screen
      .getAllByRole('row')
      .slice(1)
      .map((row) => within(row).getAllByRole('cell')[1].textContent)
    expect(numbers).toEqual(['LR-261020-0003', 'LR-261025-0001'])

    await user.click(screen.getAllByRole('checkbox', { name: 'Sélectionner la ligne' })[0])
    const bar = screen.getByRole('region', { name: 'Actions sur la sélection' })
    expect(within(bar).getByRole('button', { name: 'Exporter la sélection (CSV)' })).toBeInTheDocument()
    // Cocher une ligne n'ouvre pas le tiroir
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('FEFO', () => {
  it('colore la durée de vie restante : rouge à 2 jours, orange à 5, verte au-delà', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 10, 10, 9, 0))
    const line = (lotId: number, expiry: string) => ({
      lot: lotId,
      lot_number: `LR-000${lotId}`,
      expiry_date: expiry,
      date_type: 'DLC',
      location_code: 'MPE-FP-01',
      available: '100.000',
      take: '100.000',
    })
    mockApi({
      '/api/auth/me/': { body: TEST_USER },
      '/api/referentiel/sites/': { body: paginated([{ id: 4, code: 'MPE', name: 'Entrepôt' }]) },
      '/api/stocks/fefo/': {
        body: {
          article_code: 'MP-LAI-CREME35',
          unit: 'kg',
          site_code: 'MPE',
          requested: '300',
          covered: '300.000',
          missing: '0.000',
          lines: [line(1, '2026-11-12'), line(2, '2026-11-15'), line(3, '2026-11-30')],
        },
      },
    })
    renderApp('/fefo')
    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Code article'), 'MP-LAI-CREME35')
    await user.type(screen.getByLabelText('Quantité à servir'), '300')
    await user.click(screen.getByRole('button', { name: 'Proposer les lots' }))

    expect(await screen.findByText('2 j restants')).toHaveClass('freshness-text-danger')
    expect(screen.getByText('5 j restants')).toHaveClass('freshness-text-warn')
    expect(screen.getByText('20 j restants')).toHaveClass('freshness-text-ok')
  })
})

describe('Températures', () => {
  it('trace la courbe de chaque chambre froide avec ses seuils', async () => {
    mockApi({
      '/api/auth/me/': { body: TEST_USER },
      '/api/stocks/temperatures/latest/': {
        body: [
          {
            location: 3,
            location_code: 'MPE-FP-01',
            location_name: 'Chambre froide matières',
            site_code: 'MPE',
            min_allowed: '0.0',
            max_allowed: '4.0',
            last_reading: reading(3, '6.2', false),
          },
          {
            location: 4,
            location_code: 'MPE-FN-01',
            location_name: 'Chambre froide négative',
            site_code: 'MPE',
            min_allowed: '-25.0',
            max_allowed: '-18.0',
            last_reading: null,
          },
        ],
      },
      '/api/stocks/temperatures/': {
        body: paginated([reading(3, '6.2', false), reading(2, '3.1'), reading(1, '2.8')]),
      },
    })
    renderApp('/temperatures')
    const room = await screen.findByRole('article', { name: 'MPE-FP-01' })
    const curve = await within(room).findByRole('img', {
      name: '3 derniers relevés, dont au moins un hors seuil',
    })
    // Deux seuils en pointillés (mini et maxi)
    expect(curve.querySelectorAll('line')).toHaveLength(2)
    const empty = screen.getByRole('article', { name: 'MPE-FN-01' })
    expect(within(empty).getByText('Aucun relevé')).toBeInTheDocument()
    expect(within(empty).getByText('Pas assez de relevés')).toBeInTheDocument()
  })
})

describe('Alertes', () => {
  it('filtre par criticité avec des onglets', async () => {
    const fetchMock = mockApi({
      '/api/auth/me/': { body: TEST_USER },
      '/api/stocks/alerts/open-count/': { body: { count: 3 } },
      '/api/stocks/alerts/?state=open&level=critique': { body: paginated([alert(1, 'critique')]) },
      '/api/stocks/alerts/?state=open&level=attention': {
        body: paginated([alert(2, 'attention'), alert(3, 'attention')]),
      },
      '/api/stocks/alerts/': {
        body: paginated([alert(1, 'critique'), alert(2, 'attention'), alert(3, 'attention')]),
      },
    })
    renderApp('/alertes')
    const user = userEvent.setup()
    const tabs = await screen.findByRole('tablist', { name: 'Criticité' })
    expect(await within(tabs).findByRole('tab', { name: /^Toutes\s*3$/ })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(await screen.findByText('Alerte 2')).toBeInTheDocument()

    await user.click(within(tabs).getByRole('tab', { name: /^Critique\s*1$/ }))
    expect(await screen.findByText('Alerte 1')).toBeInTheDocument()
    expect(screen.queryByText('Alerte 2')).not.toBeInTheDocument()
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes('state=open&level=critique&v=0')),
    ).toBe(true)
  })
})
