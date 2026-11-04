import { NavLink, Navigate, Outlet } from 'react-router'
import { useAuth } from '../auth/context'
import { ROLE_LABELS } from '../format'
import { AlertBadge } from './AlertBadge'

const LINKS = [
  { to: '/', label: 'Accueil', end: true },
  { to: '/articles', label: 'Articles' },
  { to: '/fournisseurs', label: 'Fournisseurs' },
  { to: '/clients', label: 'Clients' },
  { to: '/sites', label: 'Sites' },
  { to: '/commandes', label: 'Commandes' },
  { to: '/production', label: 'Production' },
  { to: '/planning', label: 'Planning' },
  { to: '/lots', label: 'Lots' },
  { to: '/stocks', label: 'Stocks' },
  { to: '/fefo', label: 'FEFO' },
  { to: '/temperatures', label: 'Températures' },
  { to: '/inventaires', label: 'Inventaires' },
  { to: '/alertes', label: 'Alertes' },
  { to: '/tracabilite', label: 'Traçabilité' },
  { to: '/rappels', label: 'Rappels' },
]

/** Cadre commun des pages : en-tête, menu, utilisateur connecté. */
export function Layout() {
  const { status, user, logout } = useAuth()

  if (status === 'chargement') return <p className="page-message">Chargement…</p>
  if (status === 'deconnecte' || !user) return <Navigate to="/connexion" replace />

  const roles = user.roles.map((role) => ROLE_LABELS[role] ?? role).join(', ')

  return (
    <div className="app">
      <header className="app-header">
        <span className="brand">ERP Brévanne Traiteur</span>
        <nav aria-label="Menu principal">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end}>
              {link.label}
              {link.to === '/alertes' && <AlertBadge />}
            </NavLink>
          ))}
        </nav>
        <div className="user">
          <span>
            {user.first_name || user.username}
            {roles && <small> · {roles}</small>}
          </span>
          <button type="button" className="link-button" onClick={() => void logout()}>
            Se déconnecter
          </button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
