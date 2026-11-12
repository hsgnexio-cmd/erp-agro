import { NavLink, Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '../auth/context'
import { canOpen } from '../auth/roles'
import { ROLE_LABELS } from '../format'
import { AlertBadge } from './AlertBadge'

type MenuLink = { to: string; label: string; end?: boolean }

// Menu latéral rangé par métier ; chaque rôle ne voit que les liens qu'il peut ouvrir
const GROUPS: { title: string | null; links: MenuLink[] }[] = [
  {
    title: null,
    links: [
      { to: '/', label: 'Accueil', end: true },
      { to: '/tableau-de-bord', label: 'Tableau de bord' },
    ],
  },
  {
    title: 'Référentiel',
    links: [
      { to: '/articles', label: 'Articles' },
      { to: '/fournisseurs', label: 'Fournisseurs' },
      { to: '/clients', label: 'Clients' },
      { to: '/sites', label: 'Sites' },
      { to: '/calendrier', label: 'Calendrier' },
    ],
  },
  {
    title: 'Approvisionnements',
    links: [
      { to: '/commandes', label: 'Achats' },
      { to: '/besoins-achat', label: "Besoins d'achat" },
    ],
  },
  {
    title: 'Stocks et lots',
    links: [
      { to: '/lots', label: 'Lots' },
      { to: '/stocks', label: 'Stocks' },
      { to: '/fefo', label: 'FEFO' },
      { to: '/temperatures', label: 'Températures' },
      { to: '/inventaires', label: 'Inventaires' },
      { to: '/alertes', label: 'Alertes' },
    ],
  },
  {
    title: 'Fabrication',
    links: [
      { to: '/plan-production', label: 'Plan de production' },
      { to: '/planning', label: 'Planning' },
      { to: '/production', label: 'Production' },
      { to: '/trs', label: 'TRS' },
    ],
  },
  {
    title: 'Commercial',
    links: [
      { to: '/previsions', label: 'Prévisions' },
      { to: '/ventes', label: 'Ventes' },
      { to: '/edi', label: 'EDI' },
      { to: '/expeditions', label: 'Expéditions' },
      { to: '/taux-de-service', label: 'Taux de service' },
    ],
  },
  {
    title: 'Qualité',
    links: [
      { to: '/tracabilite', label: 'Traçabilité' },
      { to: '/rappels', label: 'Rappels' },
    ],
  },
]

/** Cadre commun des pages : menu latéral par métier, utilisateur connecté, contenu. */
export function Layout() {
  const { status, user, logout } = useAuth()
  const location = useLocation()

  if (status === 'chargement') return <p className="page-message">Chargement…</p>
  if (status === 'deconnecte' || !user) return <Navigate to="/connexion" replace />

  const roles = user.roles.map((role) => ROLE_LABELS[role] ?? role).join(', ')

  return (
    <div className="app">
      <aside className="app-sidebar">
        <span className="brand">
          <span className="brand-mark" aria-hidden="true">
            ERP
          </span>
          ERP Brévanne Traiteur
        </span>
        <nav aria-label="Menu principal">
          {GROUPS.map((group) => {
            const links = group.links.filter((link) => canOpen(user, link.to))
            if (links.length === 0) return null
            return (
              <div className="menu-group" key={group.title ?? 'general'}>
                {group.title && <p className="menu-title">{group.title}</p>}
                {links.map((link) => (
                  <NavLink key={link.to} to={link.to} end={link.end}>
                    {link.label}
                    {link.to === '/alertes' && <AlertBadge />}
                  </NavLink>
                ))}
              </div>
            )
          })}
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
      </aside>
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
