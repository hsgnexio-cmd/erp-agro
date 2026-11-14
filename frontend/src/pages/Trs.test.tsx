import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { LineStop, Oee } from '../api/production'
import { TEST_USER, mockApi, paginated, renderApp } from '../test/utils'

const PRODUCTION = { ...TEST_USER, roles: ['production'] }
const DIRECTION = { ...TEST_USER, roles: ['direction'] }

const OEE: Oee = {
  start: '2026-10-13',
  end: '2026-11-09',
  target: '70',
  total: { oee: '64.4', availability: '66.7', performance: '100.0', quality: '96.7' },
  lines: [
    {
      line: 1, line_code: 'L1', line_name: 'Pâtes 300 g', site_code: 'NAN', capacity_per_hour: 2400,
      opening_hours: '5.00', planned_stop_hours: '0.50', unplanned_stop_hours: '1.50',
      required_hours: '4.50', produced: '7200.000', scrap: '240.000',
      oee: '64.4', availability: '66.7', performance: '100.0', quality: '96.7',
    },
  ],
  pareto: [
    { category: 'panne', label: 'Panne', planned: false, hours: '1.00', count: 1, share: '66.7' },
    { category: 'nettoyage_planifie', label: 'Nettoyage planifié', planned: true, hours: '0.50', count: 1, share: null },
  ],
}

const STOP: LineStop = {
  id: 7, line: 1, line_code: 'L1', started_at: '2026-11-08T07:00:00Z', ended_at: '2026-11-08T08:00:00Z',
  minutes: 60, category: 'panne', category_label: 'Panne', planned: false, production_order: null,
  production_order_number: null, comment: 'Moteur du convoyeur', created_at: '2026-11-08T09:00:00Z',
  created_by_name: 'marc', cancelled_at: null, cancelled_by_name: '', cancel_reason: '',
}

function mockOee(user = PRODUCTION) {
  return mockApi({
    '/api/auth/me/': { body: user },
    '/api/production/oee/': { body: OEE },
    '/api/production/line-stops/': { body: paginated([STOP]) },
    '/api/production/line-stops/7/cancel/': { body: { ...STOP, cancelled_at: '2026-11-09T10:00:00Z' } },
    '/api/referentiel/sites/': { body: paginated([{ id: 2, code: 'NAN', name: 'Usine plats chauds', site_type: 'usine' }]) },
    '/api/referentiel/production-lines/': { body: paginated([{ id: 1, code: 'L1', name: 'Pâtes 300 g' }]) },
  })
}

describe('TRS des lignes', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('affiche le TRS, ses trois taux et le Pareto des arrêts', async () => {
    mockOee(DIRECTION)
    renderApp('/trs')
    const tile = await screen.findByRole('article', { name: 'TRS' })
    expect(within(tile).getByText('64,4 %')).toHaveClass('badge-danger')
    const line = within(screen.getByRole('table', { name: 'TRS par ligne' })).getByText('L1').closest('tr')!
    expect(line).toHaveTextContent('66,7 %')
    // Disponibilité × Performance × Qualité = TRS
    const equation = screen.getByLabelText('Décomposition du TRS')
    expect(within(equation).getAllByRole('article').map((item) => item.getAttribute('aria-label'))).toEqual([
      'Disponibilité',
      'Performance',
      'Qualité',
      'TRS',
    ])
    expect(within(line).getByRole('img', { name: /^Marche .* arrêts non planifiés/ })).toBeInTheDocument()
    const pareto = screen.getByRole('table', { name: 'Pareto des arrêts' })
    expect(within(pareto).getByText('planifié')).toBeInTheDocument()
    // La direction consulte sans saisir
    expect(screen.queryByRole('form', { name: 'Saisir un arrêt' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Annuler' })).not.toBeInTheDocument()
  })

  it('la production saisit un arrêt', async () => {
    const fetchMock = mockOee()
    renderApp('/trs')
    const form = await screen.findByRole('form', { name: 'Saisir un arrêt' })
    // La liste des lignes se charge après l'affichage du formulaire
    await within(form).findByRole('option', { name: 'L1 – Pâtes 300 g' })
    await userEvent.selectOptions(within(form).getByLabelText('Ligne'), '1')
    await userEvent.type(within(form).getByLabelText('Début'), '2026-11-09T06:00')
    await userEvent.type(within(form).getByLabelText('Fin'), '2026-11-09T06:20')
    await userEvent.selectOptions(within(form).getByLabelText('Cause'), 'changement_serie')
    await userEvent.click(within(form).getByRole('button', { name: "Enregistrer l'arrêt" }))
    const call = fetchMock.mock.calls.find(
      ([url, init]) => String(url) === '/api/production/line-stops/' && init?.method === 'POST',
    )
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({
      line: 1,
      started_at: '2026-11-09T06:00',
      ended_at: '2026-11-09T06:20',
      category: 'changement_serie',
      comment: '',
    })
  })

  it('annule un arrêt avec un motif', async () => {
    const fetchMock = mockOee()
    renderApp('/trs')
    await userEvent.click(await screen.findByRole('button', { name: 'Annuler' }))
    await userEvent.type(screen.getByLabelText("Motif de l'annulation"), 'Saisi en double')
    await userEvent.click(screen.getByRole('button', { name: 'Confirmer' }))
    const call = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/line-stops/7/cancel/'))
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({ reason: 'Saisi en double' })
  })
})
