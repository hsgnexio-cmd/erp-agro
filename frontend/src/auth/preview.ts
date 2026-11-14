import { createContext, useContext } from 'react'
import type { User } from '../api/types'

/**
 * Aperçu « vue métier », réservé à l'administrateur : le menu et l'accueil s'affichent comme
 * pour un rôle donné. Ce n'est qu'un affichage : les droits réels restent ceux du compte
 * connecté, et c'est toujours le serveur qui les applique.
 */
export interface PreviewState {
  /** L'utilisateur tel qu'il faut l'afficher (le vrai, ou son aperçu dans un rôle). */
  viewUser: User | null
  previewRole: string | null
  setPreviewRole: (role: string | null) => void
}

export const PreviewContext = createContext<PreviewState | null>(null)

export function usePreview(): PreviewState {
  const preview = useContext(PreviewContext)
  if (!preview) throw new Error('usePreview doit être utilisé dans <Layout>')
  return preview
}

/** L'utilisateur vu à travers un rôle : mêmes informations, domaines de lecture de ce rôle. */
export function previewUser(user: User | null, role: string | null): User | null {
  if (!user || !role || !user.role_areas?.[role]) return user
  return { ...user, is_superuser: false, roles: [role], areas: user.role_areas[role] }
}
