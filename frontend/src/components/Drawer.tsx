import { X } from 'lucide-react'
import { type ReactNode, useEffect, useId, useRef, useState } from 'react'

export type DrawerTab = { id: string; label: string; content: ReactNode }

/**
 * Tiroir latéral droit : affiche une fiche (lot, article, alerte, création d'un OF…) par-dessus
 * la page, sans la quitter. Il se ferme avec Échap, la croix ou un clic en dehors.
 *
 * Contenu : soit `children`, soit des `tabs` (onglets internes).
 */
export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  width = 540,
  tabs,
  footer,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: ReactNode
  /** Largeur en pixels : 540 (fiche simple) ou 680 (fiche avec tableau). */
  width?: 540 | 680
  tabs?: DrawerTab[]
  /** Barre d'actions fixée en bas du tiroir. */
  footer?: ReactNode
  children?: ReactNode
}) {
  const titleId = useId()
  const panel = useRef<HTMLDivElement>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const activeTab = tabs?.find((tab) => tab.id === selected) ?? tabs?.[0]

  // À l'ouverture : le tiroir prend le focus ; à la fermeture, il le rend à l'élément d'origine
  useEffect(() => {
    if (!open) return
    const previous = document.activeElement as HTMLElement | null
    panel.current?.focus()
    return () => previous?.focus?.()
  }, [open])

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div
        ref={panel}
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        style={{ width }}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="drawer-header">
          <div className="drawer-heading">
            <h2 id={titleId}>{title}</h2>
            {subtitle && <div className="drawer-subtitle">{subtitle}</div>}
          </div>
          <button type="button" className="drawer-close" onClick={onClose} aria-label="Fermer">
            <X size={18} aria-hidden="true" />
          </button>
        </header>
        {tabs && tabs.length > 0 && (
          <div className="drawer-tabs" role="tablist">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={tab.id === activeTab?.id}
                className={tab.id === activeTab?.id ? 'drawer-tab active' : 'drawer-tab'}
                onClick={() => setSelected(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        )}
        <div className="drawer-body" role={activeTab ? 'tabpanel' : undefined}>
          {activeTab ? activeTab.content : children}
        </div>
        {footer && <footer className="drawer-footer">{footer}</footer>}
      </div>
    </div>
  )
}
