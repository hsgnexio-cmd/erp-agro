import { NavLink, Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '../auth/context'
import { canOpen } from '../auth/roles'
import { ROLE_LABELS } from '../format'
import { AlertBadge } from './AlertBadge'

const LINKS = [
  { to: '/', label: 'Accueil', end: true },
  { to: '/tableau-de-bord', label: 'Tableau de bord' },
  { to: '/articles', label: 'Articles' },
  { to: '/fournisseurs', label: 'Fournisseurs' },
  { to: '/clients', label: 'Clients' },
  { to: '/sites', label: 'Sites' },
  { to: '/calendrier', label: 'Calendrier' },
  { to: '/commandes', label: 'Achats' },
  { to: '/besoins-achat', label: "Besoins d'achat" },
  { to: '/production', label: 'Production' },
  { to: '/plan-production', label: 'Plan de production' },
  { to: '/planning', label: 'Planning' },
  { to: '/trs', label: 'TRS' },
  { to: '/lots', label: 'Lots' },
  { to: '/previsions', label: 'Prévisions' },
  { to: '/ventes', label: 'Ventes' },
  { to: '/edi', label: 'EDI' },
  { to: '/expeditions', label: 'Expéditions' },
  { to: '/taux-de-service', label: 'Taux de service' },
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
  const location = useLocation()

  if (status === 'chargement') return <p className="page-message">Chargement…</p>
  if (status === 'deconnecte' || !user) return <Navigate to="/connexion" replace />

  const roles = user.roles.map((role) => ROLE_LABELS[role] ?? role).join(', ')

  return (
    <div className="app">
      <header className="app-header">
        <span className="brand">ERP Brévanne Traiteur</span>
        <nav aria-label="Menu principal">
          {LINKS.filter((link) => canOpen(user, link.to)).map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end}>
              {link.label}
              {link.to === '/alertes' && <AlertBadge />}
            </NavLink>
          ))}
        </nav>
        <div className="user">
          <span>
            {user.first_name || user.username}
            {user.job_title ? <small> · {user.job_title}</small> : roles && <small> · {roles}</small>}
          </span>
          <button type="button" className="link-button" onClick={() => void logout()}>
            Se déconnecter
          </button>
        </div>
      </header>
      <main className="app-main">
        {canOpen(user, location.pathname) ? (
          <Outlet />
        ) : (
          <section className="page-message" role="alert">
            <h1>Accès réservé</h1>
            <p>Ton rôle ne donne pas accès à cet écran. Les droits de chaque rôle sont décrits dans le README.</p>
          </section>
        )}
      </main>
    </div>
  )
}
