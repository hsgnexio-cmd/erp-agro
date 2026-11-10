import { Link } from 'react-router'
import { useAuth } from '../auth/context'
import { canOpen } from '../auth/roles'
import { useApi } from '../hooks/useApi'

const SECTIONS = [
  { to: '/tableau-de-bord', title: 'Tableau de bord', text: 'Indicateurs de la fiche entreprise, par semaine' },
  { to: '/articles', title: 'Articles', text: 'Matières, semi-finis, produits finis, emballages' },
  { to: '/fournisseurs', title: 'Fournisseurs', text: 'Coordonnées, délais, audits' },
  { to: '/clients', title: 'Clients', text: 'Enseignes, MDD, DLC minimale à la livraison' },
  { to: '/calendrier', title: 'Calendrier', text: 'Jours fériés, fermetures, jours travaillés' },
  { to: '/sites', title: 'Sites', text: 'Usines, plateforme, entrepôt et emplacements' },
  { to: '/commandes', title: 'Achats', text: 'Commandes fournisseurs et réceptions' },
  { to: '/besoins-achat', title: "Besoins d'achat", text: 'Calcul des besoins (MRP), propositions de commandes' },
  { to: '/production', title: 'Production', text: 'Ordres de fabrication, déclarations, rendements' },
  { to: '/plan-production', title: 'Plan de production', text: 'Plan de la semaine, figé à J-2' },
  { to: '/trs', title: 'TRS des lignes', text: 'Arrêts, disponibilité, performance, qualité' },
  { to: '/planning', title: 'Planning', text: 'Charge des lignes, ordre des allergènes' },
  { to: '/previsions', title: 'Prévisions', text: 'Demande à 8 semaines, promotions, fiabilité' },
  { to: '/ventes', title: 'Ventes', text: 'Commandes clients, tarifs de vente' },
  { to: '/edi', title: 'EDI', text: 'Messages de commande des enseignes' },
  { to: '/lots', title: 'Lots', text: 'Libération, blocage, transferts, historique' },
  { to: '/stocks', title: 'Stocks', text: 'Stock par article et par site, par statut' },
  { to: '/fefo', title: 'FEFO', text: 'Quels lots utiliser en premier ?' },
  { to: '/temperatures', title: 'Températures', text: 'Relevés des chambres froides' },
  { to: '/inventaires', title: 'Inventaires', text: 'Comptage, écarts, ajustements' },
  { to: '/alertes', title: 'Alertes', text: 'Péremption, températures : à traiter' },
  { to: '/tracabilite', title: 'Traçabilité', text: 'Amont et aval d’un lot, jusqu’aux clients' },
  { to: '/rappels', title: 'Rappels', text: 'Rappels produit et clients à prévenir' },
]

export function HomePage() {
  const { user } = useAuth()
  const health = useApi<{ status: string }>('/api/health/')

  const apiStatus = health.loading ? 'verification' : health.data ? 'ok' : 'erreur'
  const statusLabel = {
    verification: 'Vérification de la connexion au serveur…',
    ok: 'Serveur et base de données connectés',
    erreur: 'Serveur injoignable',
  }[apiStatus]

  return (
    <section className="home">
      <h1>ERP Brévanne Traiteur</h1>
      <p className="subtitle">Bonjour {user?.first_name || user?.username}</p>
      <p className={`status status-${apiStatus}`} role="status">
        {statusLabel}
      </p>
      <div className="cards">
        {SECTIONS.filter((section) => canOpen(user, section.to)).map((section) => (
          <Link key={section.to} to={section.to} className="card">
            <strong>{section.title}</strong>
            <span>{section.text}</span>
          </Link>
        ))}
      </div>
    </section>
  )
}
