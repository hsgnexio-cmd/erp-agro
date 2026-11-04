import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { vi } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider'
import { AppRoutes } from '../routes'

export const TEST_USER = {
  id: 1,
  username: 'claire',
  first_name: 'Claire',
  last_name: 'Martin',
  is_superuser: false,
  roles: ['qualite'],
}

type MockResponse = { status?: number; body: unknown }

/**
 * Remplace l'API par de fausses réponses : { '/api/auth/me/': { body: … } }.
 * L'adresse la plus longue qui correspond au début de l'URL appelée est utilisée.
 */
export function mockApi(routes: Record<string, MockResponse>) {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString()
    const match = Object.keys(routes)
      .filter((path) => url.startsWith(path))
      .sort((a, b) => b.length - a.length)[0]
    if (!match) return new Response(JSON.stringify({ detail: 'Introuvable' }), { status: 404 })
    const { status = 200, body } = routes[match]
    return new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

/** Affiche l'application à une adresse donnée, comme si on l'ouvrait dans le navigateur. */
export function renderApp(route: string) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[route]}>
        <AppRoutes />
      </MemoryRouter>
    </AuthProvider>,
  )
}

export function paginated<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results }
}
