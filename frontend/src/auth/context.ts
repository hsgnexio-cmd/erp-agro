import { createContext, useContext } from 'react'
import type { User } from '../api/types'

export interface AuthState {
  status: 'chargement' | 'deconnecte' | 'connecte'
  user: User | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('useAuth doit être utilisé dans <AuthProvider>')
  return auth
}
