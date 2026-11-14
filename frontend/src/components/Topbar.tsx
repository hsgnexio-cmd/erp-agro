import { Bell, ChevronRight, Eye, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router'
import { useAuth } from '../auth/context'
import { usePreview } from '../auth/preview'
import { canOpen } from '../auth/roles'
import { ROLE_LABELS } from '../format'
import { breadcrumb } from '../navigation'
import { AlertBadge } from './AlertBadge'
import { CommandPalette } from './CommandPalette'

// Rôles proposés dans l'aperçu « vue métier » (dans cet ordre)
const PREVIEW_ROLES = ['direction', 'qualite', 'acheteur', 'production', 'commercial', 'magasinier']

/** Barre du haut : fil d'Ariane, recherche globale (Ctrl+K), aperçu par métier, alertes. */
export function Topbar() {
  const { user } = useAuth()
  const { viewUser, previewRole, setPreviewRole } = usePreview()
  const { pathname } = useLocation()
  const [searching, setSearching] = useState(false)
  const trail = breadcrumb(pathname)

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setSearching(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <header className="topbar">
      {/* Les libellés sont affichés par le style (attribut data-label) : ils ne doublent pas
          les textes de la page */}
      <nav className="breadcrumb" aria-label={`Fil d'Ariane : ${trail.join(' › ')}`}>
        {trail.map((label, index) => (
          <span key={`${index}-${label}`} className="crumb" data-label={label}>
            {index > 0 && <ChevronRight size={14} aria-hidden="true" />}
          </span>
        ))}
      </nav>
      <button type="button" className="topbar-search" onClick={() => setSearching(true)}>
        <Search size={16} aria-hidden="true" />
        <span>Rechercher…</span>
        <kbd>Ctrl K</kbd>
      </button>
      {user?.role_areas && (
        <label className="topbar-preview" title="Aperçu : tes droits réels ne changent pas">
          <Eye size={16} aria-hidden="true" />
          <select
            aria-label="Aperçu par métier"
            value={previewRole ?? ''}
            onChange={(event) => setPreviewRole(event.target.value || null)}
          >
            <option value="">Vue administrateur</option>
            {PREVIEW_ROLES.filter((role) => user.role_areas?.[role]).map((role) => (
              <option key={role} value={role}>
                Vue {ROLE_LABELS[role] ?? role}
              </option>
            ))}
          </select>
        </label>
      )}
      {canOpen(viewUser, '/alertes') && (
        <Link className="topbar-alerts" to="/alertes" title="Alertes à traiter">
          <Bell size={18} aria-hidden="true" />
          <AlertBadge />
        </Link>
      )}
      {searching && <CommandPalette onClose={() => setSearching(false)} />}
    </header>
  )
}
