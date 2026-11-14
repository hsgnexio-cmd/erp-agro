import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TEST_USER, mockApi, renderApp } from '../test/utils'

const ADMIN = {
  ...TEST_USER,
  roles: ['admin'],
  role_areas: {
    commercial: ['referentiel', 'stocks', 'qualite', 'ventes', 'prix_vente', 'previsions', 'pilotage'],
    production: ['referentiel', 'stocks', 'qualite', 'achats', 'mrp', 'production', 'pilotage'],
  },
}

const BASE = {
  '/api/health/': { body: { status: 'ok' } },
  '/api/stocks/alerts/open-count/': { body: { count: 0 } },
}

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
  sessionStorage.clear()
})

describe('Cadre de l’application', () => {
  it('cherche un lot avec Ctrl+K et ouvre le résultat', async () => {
    const fetchMock = mockApi({
      ...BASE,
      '/api/auth/me/': { body: TEST_USER },
      '/api/pilotage/search/': {
        body: {
          results: [
            { type: 'lot', label: 'LR-261109-0004', detail: 'MP-LAI-CREME35 – Crème', url: '/lots/7' },
          ],
        },
      },
      '/api/stocks/lots/7/': { status: 404, body: { detail: 'Introuvable' } },
    })
    renderApp('/')
    const user = userEvent.setup()
    await screen.findByText('Bonjour Claire')

    await user.keyboard('{Control>}k{/Control}')
    const dialog = await screen.findByRole('dialog', { name: 'Recherche globale' })
    await user.type(within(dialog).getByLabelText("Rechercher dans l'ERP"), 'LR-2611')
    expect(await within(dialog).findByText('LR-261109-0004')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/pilotage/search/?q=LR-2611')).toBe(true)

    await user.keyboard('{Enter}')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).startsWith('/api/stocks/lots/7/')),
    ).toBe(true)
  })

  it("montre à l'administrateur le menu d'un métier, sans changer ses droits", async () => {
    mockApi({ ...BASE, '/api/auth/me/': { body: ADMIN } })
    renderApp('/')
    const user = userEvent.setup()
    const menu = await screen.findByRole('navigation', { name: 'Menu principal' })
    expect(within(menu).getByRole('link', { name: 'Production' })).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Aperçu par métier'), 'commercial')
    expect(within(menu).queryByRole('link', { name: 'Production' })).not.toBeInTheDocument()
    expect(within(menu).getByRole('link', { name: 'Ventes' })).toBeInTheDocument()
    expect(screen.getByText(/Tes droits réels ne changent pas/)).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Aperçu par métier'), '')
    expect(within(menu).getByRole('link', { name: 'Production' })).toBeInTheDocument()
  })

  it("ne propose pas l'aperçu par métier aux autres rôles", async () => {
    mockApi({ ...BASE, '/api/auth/me/': { body: TEST_USER } })
    renderApp('/')
    await screen.findByText('Bonjour Claire')
    expect(screen.queryByLabelText('Aperçu par métier')).not.toBeInTheDocument()
  })

  it('replie et déplie le menu, et retient le choix', async () => {
    mockApi({ ...BASE, '/api/auth/me/': { body: TEST_USER } })
    const { container } = renderApp('/')
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'Replier le menu' }))
    expect(container.querySelector('.app')).toHaveClass('menu-collapsed')
    expect(localStorage.getItem('erp-menu-replie')).toBe('1')
    await user.click(screen.getByRole('button', { name: 'Déplier le menu' }))
    expect(container.querySelector('.app')).not.toHaveClass('menu-collapsed')
  })

  it("affiche le fil d'Ariane de l'écran ouvert", async () => {
    mockApi({
      ...BASE,
      '/api/auth/me/': { body: TEST_USER },
      '/api/stocks/lots/': { body: { count: 0, next: null, previous: null, results: [] } },
    })
    renderApp('/lots')
    expect(
      await screen.findByRole('navigation', { name: "Fil d'Ariane : Stocks et lots › Lots" }),
    ).toBeInTheDocument()
  })
})
