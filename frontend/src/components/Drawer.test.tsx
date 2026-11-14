import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { Drawer } from './Drawer'

describe('Drawer (tiroir latéral)', () => {
  it("n'affiche rien tant qu'il est fermé", () => {
    render(
      <Drawer open={false} onClose={() => {}} title="Lot LR-1">
        Contenu
      </Drawer>,
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('affiche le titre, le contenu et le pied, à la largeur demandée', () => {
    render(
      <Drawer
        open
        onClose={() => {}}
        title="Lot LR-261109-0004"
        subtitle="Crème fraîche 35 % MG"
        width={680}
        footer={<button type="button">Bloquer</button>}
      >
        <p>Stock : 169,2 kg</p>
      </Drawer>,
    )
    const dialog = screen.getByRole('dialog', { name: 'Lot LR-261109-0004' })
    expect(dialog).toHaveStyle({ width: '680px' })
    expect(screen.getByText('Crème fraîche 35 % MG')).toBeInTheDocument()
    expect(screen.getByText('Stock : 169,2 kg')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Bloquer' })).toBeInTheDocument()
  })

  it('se ferme avec la croix, la touche Échap ou un clic en dehors, pas avec un clic dedans', async () => {
    const onClose = vi.fn()
    const { container } = render(
      <Drawer open onClose={onClose} title="Fiche">
        <p>Contenu</p>
      </Drawer>,
    )
    const user = userEvent.setup()
    await user.click(screen.getByText('Contenu'))
    expect(onClose).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Fermer' }))
    await user.keyboard('{Escape}')
    await user.click(container.querySelector('.drawer-backdrop')!)
    expect(onClose).toHaveBeenCalledTimes(3)
  })

  it("change d'onglet", async () => {
    render(
      <Drawer
        open
        onClose={() => {}}
        title="Article"
        tabs={[
          { id: 'fiche', label: 'Fiche', content: <p>Durée de vie : 8 jours</p> },
          { id: 'nomenclature', label: 'Nomenclature', content: <p>Carottes : 0,22 kg</p> },
        ]}
      />,
    )
    const user = userEvent.setup()
    expect(screen.getByRole('tab', { name: 'Fiche' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('Durée de vie : 8 jours')).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Nomenclature' }))
    expect(screen.getByText('Carottes : 0,22 kg')).toBeInTheDocument()
    expect(screen.queryByText('Durée de vie : 8 jours')).not.toBeInTheDocument()
  })

  it('rend le focus au bouton qui a ouvert le tiroir', async () => {
    function Example() {
      const [open, setOpen] = useState(false)
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            Ouvrir la fiche
          </button>
          <Drawer open={open} onClose={() => setOpen(false)} title="Fiche">
            Contenu
          </Drawer>
        </>
      )
    }
    render(<Example />)
    const user = userEvent.setup()
    const opener = screen.getByRole('button', { name: 'Ouvrir la fiche' })
    await user.click(opener)
    expect(screen.getByRole('dialog')).toHaveFocus()
    await user.keyboard('{Escape}')
    expect(opener).toHaveFocus()
  })
})
