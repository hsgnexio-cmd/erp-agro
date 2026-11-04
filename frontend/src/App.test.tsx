import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TEST_USER, mockApi, renderApp } from './test/utils'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Connexion', () => {
  it("affiche la page de connexion quand on n'est pas connecté", async () => {
    mockApi({ '/api/auth/me/': { status: 403, body: { detail: 'Non connecté' } } })
    renderApp('/')

    expect(await screen.findByRole('button', { name: 'Se connecter' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'ERP Brévanne Traiteur' })).toBeInTheDocument()
  })

  it('affiche un message clair si le mot de passe est faux', async () => {
    mockApi({
      '/api/auth/me/': { status: 403, body: {} },
      '/api/auth/csrf/': { body: { detail: 'ok' } },
      '/api/auth/login/': {
        status: 400,
        body: { detail: 'Identifiant ou mot de passe incorrect.' },
      },
    })
    renderApp('/connexion')
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Identifiant'), 'claire')
    await user.type(screen.getByLabelText('Mot de passe'), 'faux')
    await user.click(screen.getByRole('button', { name: 'Se connecter' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Identifiant ou mot de passe incorrect.',
    )
  })

  it("ouvre l'accueil après une connexion réussie", async () => {
    const fetchMock = mockApi({
      '/api/auth/me/': { status: 403, body: {} },
      '/api/auth/csrf/': { body: { detail: 'ok' } },
      '/api/auth/login/': { body: TEST_USER },
      '/api/health/': { body: { status: 'ok' } },
    })
    renderApp('/connexion')
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('Identifiant'), 'claire')
    await user.type(screen.getByLabelText('Mot de passe'), 'motdepasse')
    await user.click(screen.getByRole('button', { name: 'Se connecter' }))

    expect(await screen.findByText('Bonjour Claire')).toBeInTheDocument()
    expect(await screen.findByText('Serveur et base de données connectés')).toBeInTheDocument()
    expect(screen.getByText(/Qualité/)).toBeInTheDocument()

    const loginCall = fetchMock.mock.calls.find(([url]) => url === '/api/auth/login/')
    expect(JSON.parse(loginCall?.[1]?.body as string)).toEqual({
      username: 'claire',
      password: 'motdepasse',
    })
  })
})
