import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { LotDetail } from '../api/types'
import { TEST_USER, mockApi, paginated, renderApp } from '../test/utils'

const QUALITY = { ...TEST_USER, roles: ['qualite'] }
const STOREKEEPER = { ...TEST_USER, roles: ['magasinier'] }

const LOT: LotDetail = {
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
  location_code: 'MPE-QUAR',
  site_code: 'MPE',
  status: 'quarantaine',
  status_label: 'Quarantaine',
  block_reason: '',
  reception_number: 'REC-2026-00001',
  created_at: '2026-10-25T07:30:00Z',
  stock_by_location: [
    {
      location: 5,
      location_code: 'MPE-QUAR',
      location_name: 'Quarantaine',
      site_code: 'MPE',
      quantity: '400.000',
    },
  ],
  status_changes: [],
}

const LOCATIONS = paginated([
  { id: 3, code: 'MPE-FP-01', name: 'Chambre froide', temperature_class: 'froid_positif' },
  { id: 1, code: 'MPE-AMB-01', name: 'Magasin ambiant', temperature_class: 'ambiant' },
])

function lotRoutes(user: object) {
  return {
    '/api/auth/me/': { body: user },
    '/api/stocks/lots/9/': { body: LOT },
    '/api/stocks/movements/': { body: paginated([]) },
    '/api/referentiel/locations/': { body: LOCATIONS },
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Fiche lot', () => {
  it('la qualité peut libérer un lot en quarantaine', async () => {
    const fetchMock = mockApi({
      ...lotRoutes(QUALITY),
      '/api/stocks/lots/9/release/': { body: { ...LOT, status: 'libere' } },
    })
    renderApp('/lots/9')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Libérer' }))
    expect(await screen.findByText('Lot libéré.')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/stocks/lots/9/release/')).toBe(true)
    // Le magasinier transfère, pas la qualité
    expect(screen.queryByRole('button', { name: 'Transférer' })).not.toBeInTheDocument()
  })

  it('le magasinier transfère vers un emplacement à la bonne température', async () => {
    const fetchMock = mockApi({
      ...lotRoutes(STOREKEEPER),
      '/api/stocks/lots/9/transfer/': { body: LOT },
    })
    renderApp('/lots/9')
    const user = userEvent.setup()

    const destination = await screen.findByLabelText('Vers')
    await screen.findByRole('option', { name: 'MPE-FP-01 – Chambre froide' })
    // La crème ne peut pas aller en magasin ambiant : l'emplacement n'est pas proposé
    expect(screen.queryByRole('option', { name: /MPE-AMB-01/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Libérer' })).not.toBeInTheDocument()

    await user.selectOptions(destination, '3')
    await user.type(screen.getByLabelText('Quantité (kg)'), '150')
    await user.click(screen.getByRole('button', { name: 'Transférer' }))

    expect(await screen.findByText('Transfert enregistré.')).toBeInTheDocument()
    const call = fetchMock.mock.calls.find(([url]) => url === '/api/stocks/lots/9/transfer/')
    expect(JSON.parse(call?.[1]?.body as string)).toEqual({
      from_location: 5,
      to_location: 3,
      quantity: '150',
      reason: '',
    })
  })

  it('affiche le motif quand le serveur refuse', async () => {
    mockApi({
      ...lotRoutes(QUALITY),
      '/api/stocks/lots/9/block/': {
        status: 400,
        body: { reason: ['Indique le motif de ce changement de statut.'] },
      },
    })
    renderApp('/lots/9')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Bloquer' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Indique le motif')
  })
})

describe('État des stocks et FEFO', () => {
  it('affiche le stock par statut', async () => {
    mockApi({
      '/api/auth/me/': { body: TEST_USER },
      '/api/referentiel/sites/': { body: paginated([{ id: 4, code: 'MPE', name: 'Entrepôt' }]) },
      '/api/stocks/summary/': {
        body: [
          {
            article: 20,
            article_code: 'MP-LAI-CREME35',
            article_name: 'Crème fraîche 35 % MG',
            unit: 'kg',
            site_code: 'MPE',
            released: '500.000',
            quarantine: '0.000',
            blocked: '100.000',
            total: '600.000',
          },
        ],
      },
    })
    renderApp('/stocks')

    expect(await screen.findByText('500 kg')).toBeInTheDocument()
    expect(screen.getByText('100 kg')).toBeInTheDocument()
    expect(screen.getByText('600 kg')).toBeInTheDocument()
  })

  it('propose les lots dans l’ordre FEFO', async () => {
    mockApi({
      '/api/auth/me/': { body: TEST_USER },
      '/api/referentiel/sites/': { body: paginated([{ id: 4, code: 'MPE', name: 'Entrepôt' }]) },
      '/api/stocks/fefo/': {
        body: {
          article_code: 'MP-LAI-CREME35',
          unit: 'kg',
          site_code: 'MPE',
          requested: '300',
          covered: '250.000',
          missing: '50.000',
          lines: [
            {
              lot: 9,
              lot_number: 'LR-261025-0001',
              expiry_date: '2026-11-13',
              date_type: 'DLC',
              location_code: 'MPE-FP-01',
              available: '250.000',
              take: '250.000',
            },
          ],
        },
      },
    })
    renderApp('/fefo')
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Code article'), 'MP-LAI-CREME35')
    await user.type(screen.getByLabelText('Quantité à servir'), '300')
    await user.click(screen.getByRole('button', { name: 'Proposer les lots' }))

    expect(await screen.findByRole('link', { name: 'LR-261025-0001' })).toBeInTheDocument()
    expect(screen.getByText(/il manque 50 kg/)).toBeInTheDocument()
  })
})
