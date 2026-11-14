import { LogOut, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { useMemo, useState } from 'react'
import { NavLink, Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '../auth/context'
import { PreviewContext, previewUser } from '../auth/preview'
import { canOpen } from '../auth/roles'
import { ROLE_LABELS } from '../format'
import { GROUPS } from '../navigation'
import { AlertBadge } from './AlertBadge'
import { Topbar } from './Topbar'

const COLLAPSED_KEY = 'erp-menu-replie'
const PREVIEW_KEY = 'erp-apercu-role'

function stored(storage: Storage, key: string): string | null {
  try {
    return storage.getItem(key)
  } catch {
    return null
  }
}

function store(storage: Storage, key: string, value: string | null): void {
  try {
    if (value === null) storage.removeItem(key)
    else storage.setItem(key, value)
  } catch {
    // Stockage indisponible (navigation privée) : le réglage ne sera pas mémorisé
  }
}

/** Cadre commun des pages : menu latéral par métier, barre du haut, contenu. */
export function Layout() {
  const { status, user, logout } = useAuth()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(() => stored(localStorage, COLLAPSED_KEY) === '1')
  const [previewRole, setPreviewRoleState] = useState(() => stored(sessionStorage, PREVIEW_KEY))

  const preview = useMemo(() => {
    const role = user?.role_areas?.[previewRole ?? ''] ? previewRole : null
    return {
      viewUser: previewUser(user, role),
      previewRole: role,
      setPreviewRole: (next: string | null) => {
        store(sessionStorage, PREVIEW_KEY, next)
        setPreviewRoleState(next)
      },
    }
  }, [user, previewRole])

  if (status === 'chargement') return <p className="page-message">Chargement…</p>
  if (status === 'deconnecte' || !user) return <Navigate to="/connexion" replace />

  const viewUser = preview.viewUser
  const roles = user.roles.map((role) => ROLE_LABELS[role] ?? role).join(', ')

  function toggleMenu() {
    store(localStorage, COLLAPSED_KEY, collapsed ? null : '1')
    setCollapsed(!collapsed)
  }

  return (
    <PreviewContext.Provider value={preview}>
      <div className={collapsed ? 'app menu-collapsed' : 'app'}>
        <aside className="app-sidebar">
          <div className="sidebar-head">
            <span className="brand">
              <span className="brand-mark" aria-hidden="true">
                ERP
              </span>
              <span className="brand-name">Brévanne Traiteur</span>
            </span>
            <button
              type="button"
              className="icon-button"
              onClick={toggleMenu}
              aria-label={collapsed ? 'Déplier le menu' : 'Replier le menu'}
              title={collapsed ? 'Déplier le menu' : 'Replier le menu'}
            >
              {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
            </button>
          </div>
          <nav aria-label="Menu principal">
            {GROUPS.map((group) => {
              const links = group.links.filter((link) => canOpen(viewUser, link.to))
              if (links.length === 0) return null
              return (
                <div className="menu-group" key={group.title ?? 'general'}>
                  {group.title && <p className="menu-title">{group.title}</p>}
                  {links.map((link) => (
                    <NavLink key={link.to} to={link.to} end={link.end} title={link.label}>
                      <link.icon className="menu-icon" size={17} aria-hidden="true" />
                      <span className="menu-label">{link.label}</span>
                      {link.to === '/alertes' && <AlertBadge />}
                    </NavLink>
                  ))}
                </div>
              )
            })}
          </nav>
          <div className="user">
            <span className="user-name">
              {user.first_name || user.username}
              {user.job_title ? <small> · {user.job_title}</small> : roles && <small> · {roles}</small>}
            </span>
            <button type="button" className="link-button" onClick={() => void logout()}>
              <LogOut size={15} aria-hidden="true" />
              <span className="menu-label">Se déconnecter</span>
            </button>
          </div>
        </aside>
        <div className="app-body">
          <Topbar />
          {preview.previewRole && (
            <p className="preview-banner" role="status">
              Aperçu de la vue {ROLE_LABELS[preview.previewRole] ?? preview.previewRole} : le menu et
              l'accueil sont filtrés comme pour ce métier. Tes droits réels ne changent pas.
            </p>
          )}
          <main className="app-main">
            {canOpen(user, location.pathname) ? (
              <Outlet />
            ) : (
              <section className="page-message" role="alert">
                <h1>Accès réservé</h1>
                <p>
                  Ton rôle ne donne pas accès à cet écran. Les droits de chaque rôle sont décrits dans le
                  README.
                </p>
              </section>
            )}
          </main>
        </div>
      </div>
    </PreviewContext.Provider>
  )
}
