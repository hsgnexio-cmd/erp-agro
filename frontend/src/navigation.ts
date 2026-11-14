import {
  Bell,
  Boxes,
  Building2,
  Calculator,
  CalendarDays,
  CalendarRange,
  ChartGantt,
  ClipboardList,
  Factory,
  FileInput,
  Gauge,
  GitBranch,
  Hourglass,
  House,
  LayoutDashboard,
  type LucideIcon,
  Package,
  Percent,
  Receipt,
  Send,
  ShieldAlert,
  ShoppingCart,
  Store,
  Thermometer,
  TrendingUp,
  Truck,
  Warehouse,
} from 'lucide-react'

export type MenuLink = { to: string; label: string; icon: LucideIcon; end?: boolean }
export type MenuGroup = { title: string | null; links: MenuLink[] }

/**
 * Menu de l'application, rangé par métier. Les titres de groupe ne reprennent jamais le libellé
 * d'un lien (« Achats », « Stocks », « Production », « Ventes »).
 */
export const GROUPS: MenuGroup[] = [
  {
    title: null,
    links: [
      { to: '/', label: 'Accueil', icon: House, end: true },
      { to: '/tableau-de-bord', label: 'Tableau de bord', icon: LayoutDashboard },
    ],
  },
  {
    title: 'Référentiel',
    links: [
      { to: '/articles', label: 'Articles', icon: Package },
      { to: '/fournisseurs', label: 'Fournisseurs', icon: Truck },
      { to: '/clients', label: 'Clients', icon: Store },
      { to: '/sites', label: 'Sites', icon: Building2 },
      { to: '/calendrier', label: 'Calendrier', icon: CalendarDays },
    ],
  },
  {
    title: 'Approvisionnements',
    links: [
      { to: '/commandes', label: 'Achats', icon: ShoppingCart },
      { to: '/besoins-achat', label: "Besoins d'achat", icon: Calculator },
    ],
  },
  {
    title: 'Stocks et lots',
    links: [
      { to: '/lots', label: 'Lots', icon: Boxes },
      { to: '/stocks', label: 'Stocks', icon: Warehouse },
      { to: '/fefo', label: 'FEFO', icon: Hourglass },
      { to: '/temperatures', label: 'Températures', icon: Thermometer },
      { to: '/inventaires', label: 'Inventaires', icon: ClipboardList },
      { to: '/alertes', label: 'Alertes', icon: Bell },
    ],
  },
  {
    title: 'Fabrication',
    links: [
      { to: '/plan-production', label: 'Plan de production', icon: CalendarRange },
      { to: '/planning', label: 'Planning', icon: ChartGantt },
      { to: '/production', label: 'Production', icon: Factory },
      { to: '/trs', label: 'TRS', icon: Gauge },
    ],
  },
  {
    title: 'Commercial',
    links: [
      { to: '/previsions', label: 'Prévisions', icon: TrendingUp },
      { to: '/ventes', label: 'Ventes', icon: Receipt },
      { to: '/edi', label: 'EDI', icon: FileInput },
      { to: '/expeditions', label: 'Expéditions', icon: Send },
      { to: '/taux-de-service', label: 'Taux de service', icon: Percent },
    ],
  },
  {
    title: 'Qualité',
    links: [
      { to: '/tracabilite', label: 'Traçabilité', icon: GitBranch },
      { to: '/rappels', label: 'Rappels', icon: ShieldAlert },
    ],
  },
]

// Troisième niveau du fil d'Ariane, d'après le dernier segment de l'adresse
const DETAIL_LABELS: Record<string, string> = {
  nouvelle: 'Création',
  nouveau: 'Création',
  reception: 'Réception',
  declaration: 'Déclaration',
  preparation: 'Préparation',
  simulation: 'Simulation',
}

/** Fil d'Ariane d'une adresse : module, écran, puis détail s'il y en a un. */
export function breadcrumb(pathname: string): string[] {
  const segments = pathname.split('/').filter(Boolean)
  if (segments.length === 0) return ['Accueil']
  // « /tarifs-vente » n'est pas dans le menu : il se range avec les ventes
  const first = segments[0] === 'tarifs-vente' ? 'ventes' : segments[0]
  for (const group of GROUPS) {
    const link = group.links.find((item) => item.to === `/${first}`)
    if (!link) continue
    const trail = group.title ? [group.title, link.label] : [link.label]
    if (segments[0] === 'tarifs-vente') trail.push('Tarifs de vente')
    else if (segments.length > 1) trail.push(DETAIL_LABELS[segments[segments.length - 1]] ?? 'Fiche')
    return trail
  }
  return []
}
