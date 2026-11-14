import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TEST_USER, mockApi, paginated, renderApp } from '../test/utils'

const CRITICAL = {
  id: 7,
  alert_type: 'temperature',
  alert_type_label: 'Écart de température',
  level: 'critique',
  level_label: 'Critique',
  message: '7,8 °C en NAN-CF-SF (limites 0 à 4 °C)',
  lot: 12,
  lot_number: 'LR-261109-0004',
  location: 3,
  location_code: 'NAN-CF-SF',
  created_at: '2026-11-14T08:00:00+01:00',
  is_open: true,
  resolved_at: null,
  resolved_by_name: null,
  resolution_comment: '',
}

const BASE = {
  '/api/auth/me/': { body: TEST_USER },
  '/api/health/': { body: { status: 'ok' } },
  '/api/stocks/alerts/open-count/': { body: { count: 47 } },
  '/api/stocks/lots/': { body: paginated([{ id: 1 }, { id: 2 }, { id: 3 }]) },
}

describe('Accueil', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('affiche la date, la semaine ISO et le statut du système', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 10, 14, 9, 0))
    mockApi({ ...BASE, '/api/stocks/alerts/': { body: paginated([]) } })
    renderApp('/')
    expect(await screen.findByText('Bonjour Claire')).toBeInTheDocument()
    expect(screen.getByText('samedi 14 novembre 2026')).toBeInTheDocument()
    expect(screen.getByText('Semaine S46')).toBeInTheDocument()
    expect(await screen.findByText('Serveur et base de données connectés')).toBeInTheDocument()
  })

  it('met en avant les alertes critiques dans « Urgences du jour »', async () => {
    mockApi({ ...BASE, '/api/stocks/alerts/': { body: paginated([CRITICAL]) } })
    renderApp('/')
    const urgencies = await screen.findByRole('region', { name: 'Urgences du jour' })
    expect(within(urgencies).getByText('1 critique')).toBeInTheDocument()
    expect(within(urgencies).getByText('47 alertes à traiter en tout')).toBeInTheDocument()
    expect(within(urgencies).getByText('7,8 °C en NAN-CF-SF (limites 0 à 4 °C)')).toBeInTheDocument()
    expect(within(urgencies).getByRole('link', { name: 'Voir le lot' })).toHaveAttribute('href', '/lots/12')
    expect(within(urgencies).getByRole('link', { name: /Traiter les alertes/ })).toHaveAttribute(
      'href',
      '/alertes',
    )
  })

  it('rassure quand il n’y a aucune alerte critique', async () => {
    mockApi({ ...BASE, '/api/stocks/alerts/': { body: paginated([]) } })
    renderApp('/')
    const urgencies = await screen.findByRole('region', { name: 'Urgences du jour' })
    expect(within(urgencies).getByText('Aucune urgence critique.')).toBeInTheDocument()
    expect(within(urgencies).getByText(/47 alertes à traiter/)).toBeInTheDocument()
  })

  it('affiche un compteur sur les cartes, sauf quand le serveur ne répond pas', async () => {
    mockApi({ ...BASE, '/api/stocks/alerts/': { body: paginated([]) } })
    renderApp('/')
    const lots = (await screen.findByText('3 en quarantaine')).closest('a')!
    expect(lots).toHaveAttribute('href', '/lots')
    const alerts = screen.getByText('47 à traiter')
    expect(alerts).toHaveClass('urgent')
    // Aucune réponse simulée pour les articles : la carte reste, sans compteur
    const articles = screen.getByText('Matières, semi-finis, produits finis, emballages').closest('a')!
    expect(within(articles).queryByText(/articles$/)).not.toBeInTheDocument()
  })
})
