import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { type DataColumn, DataTable } from './DataTable'

type Lot = { id: number; number: string; article: string; quantity: number; status: string }

const LOTS: Lot[] = [
  { id: 1, number: 'LR-0002', article: 'Crème', quantity: 120.5, status: 'Libéré' },
  { id: 2, number: 'LR-0010', article: 'Beurre', quantity: 80, status: 'Bloqué' },
  { id: 3, number: 'LR-0001', article: 'Crème', quantity: 300, status: 'Quarantaine' },
]

const COLUMNS: DataColumn<Lot>[] = [
  { id: 'number', header: 'Lot', cell: (lot) => lot.number, sortValue: (lot) => lot.number },
  { id: 'article', header: 'Article', cell: (lot) => lot.article, sortValue: (lot) => lot.article },
  {
    id: 'quantity',
    header: 'Quantité',
    numeric: true,
    cell: (lot) => `${lot.quantity} kg`,
    sortValue: (lot) => lot.quantity,
  },
  { id: 'status', header: 'Statut', cell: (lot) => lot.status },
]

/** Numéros de lot, dans l'ordre affiché. */
const order = () =>
  screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => within(row).getAllByRole('cell')[0].textContent)

const table = (props: Partial<Parameters<typeof DataTable<Lot>>[0]> = {}) => (
  <DataTable rows={LOTS} columns={COLUMNS} rowKey={(lot) => lot.id} caption="Lots" {...props} />
)

describe('DataTable (tableau de données)', () => {
  it('aligne les chiffres à droite et laisse les lignes dans leur ordre de départ', () => {
    render(table())
    expect(screen.getByRole('table', { name: 'Lots' })).toBeInTheDocument()
    expect(order()).toEqual(['LR-0002', 'LR-0010', 'LR-0001'])
    expect(screen.getByRole('columnheader', { name: /Quantité/ })).toHaveClass('num')
    expect(screen.getByText('120.5 kg')).toHaveClass('num')
    // Une colonne sans valeur de tri n'a pas de bouton
    expect(screen.queryByRole('button', { name: /Statut/ })).not.toBeInTheDocument()
  })

  it('trie par colonne : croissant, décroissant, puis ordre de départ', async () => {
    render(table())
    const user = userEvent.setup()
    const quantity = screen.getByRole('button', { name: /Quantité/ })
    await user.click(quantity)
    expect(order()).toEqual(['LR-0010', 'LR-0002', 'LR-0001'])
    expect(screen.getByRole('columnheader', { name: /Quantité/ })).toHaveAttribute('aria-sort', 'ascending')
    await user.click(quantity)
    expect(order()).toEqual(['LR-0001', 'LR-0002', 'LR-0010'])
    await user.click(quantity)
    expect(order()).toEqual(['LR-0002', 'LR-0010', 'LR-0001'])
  })

  it('trie les textes « naturellement » (LR-0002 avant LR-0010)', async () => {
    render(table())
    await userEvent.setup().click(screen.getByRole('button', { name: /^Lot/ }))
    expect(order()).toEqual(['LR-0001', 'LR-0002', 'LR-0010'])
  })

  it('trie sur plusieurs colonnes avec Maj + clic', async () => {
    render(table())
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /Article/ }))
    // Beurre, puis les deux Crème dans leur ordre de départ
    expect(order()).toEqual(['LR-0010', 'LR-0002', 'LR-0001'])
    await user.keyboard('{Shift>}')
    await user.click(screen.getByRole('button', { name: /Quantité/ }))
    await user.click(screen.getByRole('button', { name: /Quantité/ }))
    await user.keyboard('{/Shift}')
    // Article croissant, puis quantité décroissante
    expect(order()).toEqual(['LR-0010', 'LR-0001', 'LR-0002'])
  })

  it('sélectionne des lignes et lance une action groupée', async () => {
    const block = vi.fn()
    render(table({ bulkActions: [{ label: 'Bloquer la sélection', onRun: block, danger: true }] }))
    const user = userEvent.setup()
    expect(screen.queryByRole('region', { name: 'Actions sur la sélection' })).not.toBeInTheDocument()

    const boxes = screen.getAllByRole('checkbox', { name: 'Sélectionner la ligne' })
    await user.click(boxes[0])
    await user.click(boxes[2])
    const bar = screen.getByRole('region', { name: 'Actions sur la sélection' })
    expect(within(bar).getByText('2 lignes sélectionnées')).toBeInTheDocument()

    await user.click(within(bar).getByRole('button', { name: 'Bloquer la sélection' }))
    expect(block).toHaveBeenCalledWith([LOTS[0], LOTS[2]])

    await user.click(within(bar).getByRole('button', { name: 'Tout désélectionner' }))
    expect(screen.queryByRole('region', { name: 'Actions sur la sélection' })).not.toBeInTheDocument()
  })

  it('coche et décoche toutes les lignes', async () => {
    render(table({ bulkActions: [{ label: 'Exporter', onRun: () => {} }] }))
    const user = userEvent.setup()
    await user.click(screen.getByRole('checkbox', { name: 'Tout sélectionner' }))
    expect(screen.getByText('3 lignes sélectionnées')).toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: 'Tout sélectionner' }))
    expect(screen.queryByText(/sélectionnée/)).not.toBeInTheDocument()
  })

  it("ouvre une ligne au clic, sans que la case à cocher ne l'ouvre", async () => {
    const open = vi.fn()
    render(table({ onRowClick: open, bulkActions: [{ label: 'Exporter', onRun: () => {} }] }))
    const user = userEvent.setup()
    await user.click(screen.getAllByRole('checkbox', { name: 'Sélectionner la ligne' })[1])
    expect(open).not.toHaveBeenCalled()
    await user.click(screen.getByText('LR-0010'))
    expect(open).toHaveBeenCalledWith(LOTS[1])
  })

  it('affiche un message quand il n’y a aucune ligne', () => {
    render(table({ rows: [], empty: 'Aucun lot ne correspond.' }))
    expect(screen.getByText('Aucun lot ne correspond.')).toBeInTheDocument()
  })
})
