import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

describe("Page d'accueil", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("affiche le titre de l'ERP", () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    render(<App />)
    expect(screen.getByRole('heading', { name: 'ERP Brévanne Traiteur' })).toBeInTheDocument()
  })

  it('indique que le serveur est connecté quand /api/health/ répond', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response('{}', { status: 200 }))))
    render(<App />)
    expect(await screen.findByText('Serveur et base de données connectés')).toBeInTheDocument()
  })
})
