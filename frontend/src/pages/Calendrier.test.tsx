import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { CompanyCalendar } from '../api/calendar'
import { TEST_USER, mockApi, renderApp } from '../test/utils'

const CALENDAR: CompanyCalendar = {
  year: 2026,
  rules: [{ activity: 'Production (usines NAN, REN)', days: 'du lundi au vendredi' }],
  holidays: [
    { date: '2026-11-11', label: 'Armistice 1918', weekday: 'mercredi' },
    { date: '2026-08-15', label: 'Assomption', weekday: 'samedi' },
  ],
  closures: [
    { id: 1, site_code: 'NAN', site_name: 'Usine plats chauds', start_date: '2026-11-13', end_date: '2026-11-13', reason: 'Pont' },
  ],
}

describe('Calendrier', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('affiche les jours fériés, les fermetures et les jours travaillés', async () => {
    mockApi({ '/api/auth/me/': { body: TEST_USER }, '/api/referentiel/calendar/': { body: CALENDAR } })
    renderApp('/calendrier')
    const holidays = await screen.findByRole('table', { name: 'Jours fériés' })
    expect(within(holidays).getByText('Armistice 1918')).toBeInTheDocument()
    expect(within(holidays).getByText('tombe un week-end')).toBeInTheDocument()
    const closures = screen.getByRole('table', { name: 'Fermetures exceptionnelles' })
    expect(within(closures).getByText('Pont')).toBeInTheDocument()
    expect(screen.getByText(/du lundi au vendredi, hors jours fériés/)).toBeInTheDocument()
    // Vue de l'année : le 11 novembre est férié, le 13 est une fermeture de site
    const year = screen.getByLabelText('Calendrier 2026')
    expect(within(year).getByTitle('Armistice 1918')).toHaveClass('day-holiday')
    expect(within(year).getByTitle('Fermeture NAN : Pont')).toHaveClass('day-closed')
  })
})
