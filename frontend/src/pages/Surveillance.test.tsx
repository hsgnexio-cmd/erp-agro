import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Alert, InventoryDetail } from '../api/monitoring'
import { TEST_USER, mockApi, paginated, renderApp } from '../test/utils'

const STOREKEEPER = { ...TEST_USER, roles: ['magasinier'] }

const COLD_ROOM = {
  location: 3,
  location_code: 'MPE-FP-01',
  location_name: 'Chambre froide matières',
  site_code: 'MPE',
  min_allowed: '0.0',
  max_allowed: '4.0',
  last_reading: null,
}

const INVENTORY: InventoryDetail = {
  id: 2,
  number: 'INV-2026-00002',
  site: 4,
  site_code: 'MPE',
  location: 3,
  location_code: 'MPE-FP-01',
  status: 'en_cours',
  status_label: 'En cours',
  comment: '',
  opened_at: '2026-11-04T08:00:00Z',
  opened_by_name: 'marc',
  closed_at: null,
  closed_by_name: null,
  line_count: 1,
  lines: [
    {
      id: 21,
      lot: 9,
      lot_number: 'LR-261025-0001',
      article_code: 'MP-LAI-CREME35',
      article_name: 'Crème fraîche 35 % MG',
      unit: 'kg',
      expiry_date: '2026-11-13',
      location: 3,
      location_code: 'MPE-FP-01',
      expected_quantity: null,
      counted_quantity: null,
      difference: null,
      added_during_count: false,
    },
  ],
}

const ALERT: Alert = {
  id: 5,
  alert_type: 'peremption_proche',
  alert_type_label: 'Péremption proche',
  level: 'attention',
  level_label: 'Attention',
  message: 'Le lot LR-261025-0001 arrive à DLC dans 2 jour(s).',
  lot: 9,
  lot_number: 'LR-261025-0001',
  location: null,
  location_code: null,
  created_at: '2026-11-04T06:00:00Z',
  is_open: true,
  resolved_at: null,
  resolved_by_name: null,
  resolution_comment: '',
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Températures', () => {
  it("annonce l'écart et les lots bloqués", async () => {
    mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/stocks/temperatures/latest/': { body: [COLD_ROOM] },
      // Lecture de l'historique (GET …/?v=0), à distinguer de l'enregistrement (POST)
      '/api/stocks/temperatures/?v': { body: paginated([]) },
      '/api/stocks/temperatures/': {
        status: 201,
        body: {
          id: 1,
          location: 3,
          location_code: 'MPE-FP-01',
          location_name: 'Chambre froide matières',
          site_code: 'MPE',
          temperature: '7.2',
          measured_at: '2026-11-04T09:00:00Z',
          min_allowed: '0.0',
          max_allowed: '4.0',
          is_compliant: false,
          user_name: 'marc',
          comment: '',
          blocked_lots: ['LR-261025-0001'],
          alert: 'Écart de température : 7,2 °C en MPE-FP-01 (limites 0 à 4 °C).',
        },
      },
    })
    renderApp('/temperatures')
    const user = userEvent.setup()

    await user.selectOptions(
      await screen.findByLabelText('Chambre froide'),
      await screen.findByRole('option', { name: 'MPE-FP-01 – Chambre froide matières' }),
    )
    await user.type(screen.getByLabelText('Température (°C)'), '7.2')
    await user.click(screen.getByRole('button', { name: 'Enregistrer le relevé' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Écart de température')
    expect(alert).toHaveTextContent('Lots bloqués automatiquement : LR-261025-0001')
  })
})

describe('Inventaire', () => {
  it('cache la quantité théorique pendant le comptage et envoie les quantités comptées', async () => {
    const fetchMock = mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/stocks/inventories/2/count/': { body: INVENTORY },
      '/api/stocks/inventories/2/': { body: INVENTORY },
      '/api/referentiel/locations/': { body: paginated([]) },
    })
    renderApp('/inventaires/2')
    const user = userEvent.setup()

    const input = await screen.findByLabelText('Compté LR-261025-0001 MPE-FP-01')
    expect(screen.queryByText('Théorique')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Voir les écarts \(1 ligne/ })).toBeDisabled()

    await user.type(input, '248')
    await user.click(screen.getByRole('button', { name: 'Enregistrer le comptage' }))

    expect(await screen.findByText('Comptage enregistré.')).toBeInTheDocument()
    const call = fetchMock.mock.calls.find(([url]) => url === '/api/stocks/inventories/2/count/')
    expect(JSON.parse(call?.[1]?.body as string)).toEqual({
      lines: [{ id: 21, counted_quantity: '248' }],
    })
  })

  it('montre les écarts avant de valider', async () => {
    const counted = {
      ...INVENTORY,
      lines: [{ ...INVENTORY.lines[0], counted_quantity: '248.000' }],
    }
    mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/stocks/inventories/2/?v=0&show_differences=1': {
        body: {
          ...counted,
          lines: [{ ...counted.lines[0], expected_quantity: '250.000', difference: '-2.000' }],
        },
      },
      '/api/stocks/inventories/2/': { body: counted },
      '/api/referentiel/locations/': { body: paginated([]) },
    })
    renderApp('/inventaires/2')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Voir les écarts' }))
    expect(await screen.findByText('-2 kg')).toBeInTheDocument()
    expect(screen.getByText('250 kg')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: "Valider l'inventaire" })).toBeInTheDocument()
  })
})

describe('Alertes', () => {
  it('affiche le compteur du menu et traite une alerte avec un commentaire', async () => {
    const fetchMock = mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/stocks/alerts/open-count/': { body: { count: 3 } },
      '/api/stocks/alerts/5/resolve/': { body: { ...ALERT, is_open: false } },
      '/api/stocks/alerts/': { body: paginated([ALERT]) },
    })
    renderApp('/alertes')
    const user = userEvent.setup()

    // Le compteur est affiché dans le menu et dans la barre du haut
    const menu = await screen.findByRole('navigation', { name: 'Menu principal' })
    expect(await within(menu).findByLabelText('3 alerte(s) à traiter')).toHaveTextContent('3')
    await user.type(await screen.findByLabelText('Commentaire alerte 5'), 'Lot utilisé en priorité')
    await user.click(screen.getByRole('button', { name: 'Marquer comme traitée' }))

    await vi.waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url === '/api/stocks/alerts/5/resolve/')
      expect(JSON.parse(call?.[1]?.body as string)).toEqual({
        comment: 'Lot utilisé en priorité',
      })
    })
  })
})
