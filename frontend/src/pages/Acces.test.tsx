import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TEST_USER, mockApi, renderApp } from '../test/utils'

// Domaines d'un magasinier, tels que renvoyés par /api/auth/me/ (matrice du serveur)
const STOREKEEPER = {
  ...TEST_USER,
  first_name: 'Sandrine',
  job_title: 'Cheffe de quai, plateforme PFN',
  roles: ['magasinier'],
  areas: ['referentiel', 'stocks', 'qualite', 'achats', 'ventes', 'pilotage'],
}

describe("Accès selon le rôle", () => {
  afterEach(() => vi.unstubAllGlobals())

  it("le menu et l'accueil n'affichent que les écrans du rôle", async () => {
    mockApi({ '/api/auth/me/': { body: STOREKEEPER }, '/api/health/': { body: { status: 'ok' } } })
    renderApp('/')
    const menu = await screen.findByRole('navigation', { name: 'Menu principal' })
    expect(within(menu).getByRole('link', { name: 'Ventes' })).toBeInTheDocument()
    expect(within(menu).getByRole('link', { name: /Lots/ })).toBeInTheDocument()
    // Tableau de bord ouvert à tous : le serveur n'y renvoie que les indicateurs du rôle
    expect(within(menu).getByRole('link', { name: 'Tableau de bord' })).toBeInTheDocument()
    expect(within(menu).queryByRole('link', { name: 'Prévisions' })).not.toBeInTheDocument()
    expect(within(menu).queryByRole('link', { name: 'TRS' })).not.toBeInTheDocument()
    expect(screen.queryByText('Demande à 8 semaines, promotions, fiabilité')).not.toBeInTheDocument()
    expect(screen.getByText('Cheffe de quai, plateforme PFN', { exact: false })).toBeInTheDocument()
  })

  it('un écran hors du rôle affiche « Accès réservé »', async () => {
    mockApi({ '/api/auth/me/': { body: STOREKEEPER } })
    renderApp('/previsions')
    expect(await screen.findByRole('heading', { name: 'Accès réservé' })).toBeInTheDocument()
  })
})
