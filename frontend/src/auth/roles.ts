import type { User } from '../api/types'

/** Vrai si l'utilisateur a l'un des rôles (un superutilisateur a tous les droits). */
export function hasRole(user: User | null, roles: string[]): boolean {
  if (!user) return false
  return user.is_superuser || user.roles.some((role) => roles.includes(role))
}

export const PURCHASING_ROLES = ['admin', 'acheteur']
export const WAREHOUSE_ROLES = ['admin', 'magasinier']
