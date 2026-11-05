import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Indicator, Indicators } from '../api/pilotage'
import { TEST_USER, mockApi, paginated, renderApp } from '../test/utils'

const DIRECTION = { ...TEST_USER, roles: ['direction'] }

function indicator(overrides: Partial<Indicator>): Indicator {
  return {
    code: 'service_rate',
    label: 'Taux de service',
    unit: '%',
    definition: 'Quantité livrée complète et à l’heure ÷ quantité commandée',
    filters: ['période (livraison demandée)', 'enseigne'],
    value: '99.2',
    target: '≥ 98,5 %',
    target_min: '98.5',
    target_max: null,
    status: 'ok',
    detail: '42 commande(s) livrable(s) sur la période',
    ...overrides,
  }
}

const INDICATORS: Indicators = {
  start: '2026-10-09',
  end: '2026-11-05',
  indicators: [
    indicator({}),
    indicator({
      code: 'markdown',
      label: 'Démarque',
      unit: '% du CA',
      value: '1.57',
      target: '≤ 1,5 % du CA',
      target_min: null,
      target_max: '1.5',
      status: 'alerte',
      detail: '7 472 € détruits ou donnés pour 474 997 € de CA',
      filters: ['période'],
    }),
    indicator({
      code: 'oee',
      label: 'TRS',
      value: null,
      target: '≥ 70 %',
      target_min: '70',
      status: 'indisponible',
      detail: 'Non disponible : l’ERP n’enregistre ni les arrêts de ligne ni les cadences réelles.',
      filters: [],
    }),
  ],
  weeks: [
    {
      start: '2026-10-09',
      end: '2026-10-11',
      label: 'S41',
      values: { service_rate: '100.0', markdown: '0.42' },
    },
    {
      start: '2026-10-12',
      end: '2026-10-18',
      label: 'S42',
      values: { service_rate: '96.0', markdown: '0.40' },
    },
  ],
}

function mockDashboard() {
  return mockApi({
    '/api/auth/me/': { body: DIRECTION },
    '/api/referentiel/sites/': {
      body: paginated([
        { id: 1, code: 'NAN', name: 'Usine plats chauds', site_type: 'usine', site_type_label: 'Usine', city: 'Nantes', active: true },
      ]),
    },
    '/api/referentiel/customers/': { body: paginated([]) },
    '/api/pilotage/indicators/': { body: INDICATORS },
  })
}

describe('Tableau de bord', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('affiche une tuile par indicateur, verte ou rouge selon l’objectif', async () => {
    mockDashboard()
    renderApp('/tableau-de-bord')

    const service = await screen.findByRole('article', { name: 'Taux de service' })
    expect(within(service).getByText('99,2 %')).toBeInTheDocument()
    expect(within(service).getByText('Objectif atteint')).toBeInTheDocument()

    const markdown = screen.getByRole('article', { name: 'Démarque' })
    expect(within(markdown).getByText('1,57 %')).toBeInTheDocument()
    expect(within(markdown).getByText('Hors objectif')).toBeInTheDocument()

    // Indicateur sans données dans l'ERP : affiché « non disponible », jamais inventé
    const oee = screen.getByRole('article', { name: 'TRS' })
    expect(within(oee).getByText('Non disponible')).toBeInTheDocument()
    expect(within(oee).getByText(/ni les arrêts de ligne/)).toBeInTheDocument()
  })

  it('montre l’évolution par semaine, avec la couleur de chaque valeur', async () => {
    mockDashboard()
    renderApp('/tableau-de-bord')

    const row = (await screen.findByRole('cell', { name: 'Taux de service' })).closest('tr')!
    expect(within(row).getByText('100 %')).toHaveClass('badge-ok')
    expect(within(row).getByText('96 %')).toHaveClass('badge-danger')
    // Le TRS n'a pas d'évolution par semaine
    expect(screen.queryByRole('cell', { name: 'TRS' })).not.toBeInTheDocument()
  })

  it('recalcule avec le site choisi', async () => {
    const fetchMock = mockDashboard()
    renderApp('/tableau-de-bord')

    await screen.findByRole('article', { name: 'Taux de service' })
    await userEvent.selectOptions(screen.getByLabelText('Site'), '1')

    // L'export pour Excel suit les mêmes filtres
    expect(screen.getByRole('link', { name: /Exporter pour Excel/ })).toHaveAttribute(
      'href',
      expect.stringContaining('/api/pilotage/indicators/export/?start='),
    )
    expect(screen.getByRole('link', { name: /Exporter pour Excel/ }).getAttribute('href')).toContain(
      'site=1',
    )
    const urls = fetchMock.mock.calls.map(([input]) => String(input))
    expect(urls.some((url) => url.includes('/api/pilotage/indicators/') && url.includes('site=1'))).toBe(
      true,
    )
  })
})
