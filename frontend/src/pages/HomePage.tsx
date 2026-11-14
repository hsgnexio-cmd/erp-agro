import { AlertTriangle, ArrowRight, CircleCheck } from 'lucide-react'
import { Link } from 'react-router'
import type { Alert } from '../api/monitoring'
import type { Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { usePreview } from '../auth/preview'
import { canOpen } from '../auth/roles'
import { useApi } from '../hooks/useApi'
import { GROUPS } from '../navigation'

// Une phrase par écran, sous son nom
const TEXTS: Record<string, string> = {
  '/tableau-de-bord': 'Les indicateurs de ton métier, par semaine',
  '/articles': 'Matières, semi-finis, produits finis, emballages',
  '/fournisseurs': 'Coordonnées, délais, audits',
  '/clients': 'Enseignes, MDD, DLC minimale à la livraison',
  '/sites': 'Usines, plateforme, entrepôt et emplacements',
  '/calendrier': 'Jours fériés, fermetures, jours travaillés',
  '/commandes': 'Commandes fournisseurs et réceptions',
  '/besoins-achat': 'Calcul des besoins (MRP), propositions de commandes',
  '/lots': 'Libération, blocage, transferts, historique',
  '/stocks': 'Stock par article et par site, par statut',
  '/fefo': 'Quels lots utiliser en premier ?',
  '/temperatures': 'Relevés des chambres froides',
  '/inventaires': 'Comptage, écarts, ajustements',
  '/alertes': 'Péremption, températures : à traiter',
  '/plan-production': 'Plan de la semaine, figé à J-2',
  '/planning': 'Charge des lignes, ordre des allergènes',
  '/production': 'Ordres de fabrication, déclarations, rendements',
  '/trs': 'Arrêts, disponibilité, performance, qualité',
  '/previsions': 'Demande à 8 semaines, promotions, fiabilité',
  '/ventes': 'Commandes clients, tarifs de vente',
  '/edi': 'Messages de commande des enseignes',
  '/expeditions': 'Bons de livraison, palettes, étiquettes',
  '/taux-de-service': 'Livré complet et à l’heure, par enseigne',
  '/tracabilite': 'Amont et aval d’un lot, jusqu’aux clients',
  '/rappels': 'Rappels produit et clients à prévenir',
}

// Compteur affiché sur la carte d'un écran : une requête légère sur une API existante (le
// serveur applique les droits de lecture) ; `urgent` le met en avant quand il n'est pas nul
const COUNTERS: Record<string, { url: string; label: (n: number) => string; urgent?: boolean }> = {
  '/alertes': { url: '/api/stocks/alerts/open-count/', label: (n) => `${n} à traiter`, urgent: true },
  '/lots': {
    url: '/api/stocks/lots/?status=quarantaine',
    label: (n) => `${n} en quarantaine`,
  },
  '/commandes': { url: '/api/achats/orders/?status=envoyee', label: (n) => `${n} à recevoir` },
  '/production': {
    url: '/api/production/orders/?status=lance',
    label: (n) => `${n} OF en cours`,
  },
  '/ventes': { url: '/api/ventes/orders/?status=recue', label: (n) => `${n} à préparer` },
  '/rappels': { url: '/api/qualite/recalls/', label: (n) => `${n} rappel${n > 1 ? 's' : ''}` },
  '/articles': { url: '/api/referentiel/articles/', label: (n) => `${n} articles` },
  '/fournisseurs': { url: '/api/referentiel/suppliers/', label: (n) => `${n} fournisseurs` },
  '/clients': { url: '/api/referentiel/customers/', label: (n) => `${n} enseignes` },
}

function Counter({ path }: { path: string }) {
  const counter = COUNTERS[path]
  const { data } = useApi<{ count: number }>(counter.url)
  if (!data) return null
  return (
    <span className={counter.urgent && data.count > 0 ? 'card-count urgent' : 'card-count'}>
      {counter.label(data.count)}
    </span>
  )
}

/** Numéro de semaine ISO (la semaine 1 contient le premier jeudi de l'année). */
function isoWeek(date: Date): number {
  const day = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  day.setUTCDate(day.getUTCDate() + 4 - (day.getUTCDay() || 7))
  const yearStart = Date.UTC(day.getUTCFullYear(), 0, 1)
  return Math.ceil(((day.getTime() - yearStart) / 86400000 + 1) / 7)
}

/** Bandeau du haut : les alertes critiques à traiter aujourd'hui. */
function Urgencies() {
  const critical = useApi<Paginated<Alert>>('/api/stocks/alerts/?state=open&level=critique')
  const open = useApi<{ count: number }>('/api/stocks/alerts/open-count/')
  if (!critical.data) return null
  const total = open.data?.count ?? critical.data.count
  if (critical.data.count === 0) {
    return (
      <section className="urgencies calm" aria-label="Urgences du jour">
        <CircleCheck size={20} aria-hidden="true" />
        <p>
          <strong>Aucune urgence critique.</strong>{' '}
          {total > 0 ? `${total} alerte${total > 1 ? 's' : ''} à traiter.` : 'Aucune alerte en attente.'}
        </p>
        {total > 0 && (
          <Link className="button secondary" to="/alertes">
            Voir les alertes
          </Link>
        )}
      </section>
    )
  }
  return (
    <section className="urgencies" aria-label="Urgences du jour">
      <header>
        <AlertTriangle size={20} aria-hidden="true" />
        <h2>Urgences du jour</h2>
        <span className="badge badge-danger">
          {critical.data.count} critique{critical.data.count > 1 ? 's' : ''}
        </span>
        <span className="urgencies-total">{total} alertes à traiter en tout</span>
      </header>
      <ul>
        {critical.data.results.slice(0, 3).map((alert) => (
          <li key={alert.id}>
            <div>
              <strong>{alert.alert_type_label}</strong>
              <span>{alert.message}</span>
            </div>
            {alert.lot && (
              <Link className="button secondary" to={`/lots/${alert.lot}`}>
                Voir le lot
              </Link>
            )}
          </li>
        ))}
      </ul>
      <Link className="button" to="/alertes">
        Traiter les alertes <ArrowRight size={16} aria-hidden="true" />
      </Link>
    </section>
  )
}

export function HomePage() {
  const { user: account } = useAuth()
  // L'accueil suit l'aperçu « vue métier » de l'administrateur
  const user = usePreview().viewUser ?? account
  const health = useApi<{ status: string }>('/api/health/')

  const apiStatus = health.loading ? 'verification' : health.data ? 'ok' : 'erreur'
  const statusLabel = {
    verification: 'Vérification de la connexion au serveur…',
    ok: 'Serveur et base de données connectés',
    erreur: 'Serveur injoignable',
  }[apiStatus]
  const today = new Date()
  const dateLabel = today.toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  return (
    <section className="home">
      <header className="cockpit">
        <div>
          <h1>Bonjour {user?.first_name || user?.username}</h1>
          <p className="cockpit-date">
            <span className="cockpit-day">{dateLabel}</span>
            <span className="cockpit-week">Semaine S{isoWeek(today)}</span>
          </p>
        </div>
        <p className={`system-status system-${apiStatus}`} role="status">
          <span className="system-dot" aria-hidden="true" />
          {statusLabel}
        </p>
      </header>

      {canOpen(user, '/alertes') && <Urgencies />}

      {GROUPS.map((group) => {
        // L'accueil lui-même n'a pas de carte
        const links = group.links.filter((link) => link.to !== '/' && canOpen(user, link.to))
        if (links.length === 0) return null
        return (
          <div className="home-group" key={group.title ?? 'pilotage'}>
            <h2>{group.title ?? 'Pilotage'}</h2>
            <div className="cards">
              {links.map((link) => (
                <Link key={link.to} to={link.to} className="card module-card">
                  <span className="module-icon" aria-hidden="true">
                    <link.icon size={18} />
                  </span>
                  <span className="module-text">
                    <strong>{link.label}</strong>
                    <span>{TEXTS[link.to]}</span>
                  </span>
                  {COUNTERS[link.to] && <Counter path={link.to} />}
                </Link>
              ))}
            </div>
          </div>
        )
      })}
    </section>
  )
}
