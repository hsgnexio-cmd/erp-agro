import type { User } from '../api/types'

/** Vrai si l'utilisateur a l'un des rôles (un superutilisateur a tous les droits). */
export function hasRole(user: User | null, roles: string[]): boolean {
  if (!user) return false
  return user.is_superuser || user.roles.some((role) => roles.includes(role))
}

export const PURCHASING_ROLES = ['admin', 'acheteur']
export const WAREHOUSE_ROLES = ['admin', 'magasinier']
export const QUALITY_ROLES = ['admin', 'qualite']
export const PRODUCTION_ROLES = ['admin', 'production']
export const SALES_ROLES = ['admin', 'commercial']

/**
 * Domaine de chaque écran (premier segment de l'adresse), comme la matrice d'accès du serveur
 * (backend/comptes/access.py). Un écran absent de cette liste est ouvert à tous.
 */
const PATH_AREAS: Record<string, string> = {
  'tableau-de-bord': 'pilotage',
  articles: 'referentiel',
  fournisseurs: 'referentiel',
  clients: 'referentiel',
  sites: 'referentiel',
  calendrier: 'referentiel',
  commandes: 'achats',
  'besoins-achat': 'mrp',
  production: 'production',
  'plan-production': 'production',
  planning: 'production',
  trs: 'production',
  previsions: 'previsions',
  ventes: 'ventes',
  edi: 'ventes',
  expeditions: 'ventes',
  'taux-de-service': 'ventes',
  'tarifs-vente': 'prix_vente',
  lots: 'stocks',
  stocks: 'stocks',
  fefo: 'stocks',
  temperatures: 'stocks',
  inventaires: 'stocks',
  alertes: 'stocks',
  tracabilite: 'qualite',
  rappels: 'qualite',
}

/** Vrai si l'utilisateur peut consulter ce domaine (un superutilisateur voit tout). */
export function canRead(user: User | null, area: string): boolean {
  if (!user) return false
  if (user.is_superuser || user.areas === undefined) return true
  return user.areas.includes(area)
}

/** Vrai si l'utilisateur peut ouvrir l'écran à cette adresse. */
export function canOpen(user: User | null, path: string): boolean {
  const area = PATH_AREAS[path.split('/').filter(Boolean)[0] ?? '']
  return area === undefined || canRead(user, area)
}

