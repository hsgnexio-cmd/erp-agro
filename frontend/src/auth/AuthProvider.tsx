import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { apiGet, apiPost } from '../api/client'
import type { User } from '../api/types'
import { AuthContext, type AuthState } from './context'

/** Garde en mémoire l'utilisateur connecté pour toute l'application. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthState['status']>('chargement')
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    apiGet<User>('/api/auth/me/')
      .then((me) => {
        setUser(me)
        setStatus('connecte')
      })
      .catch(() => setStatus('deconnecte'))
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    await apiGet('/api/auth/csrf/')
    const me = await apiPost<User>('/api/auth/login/', { username, password })
    setUser(me)
    setStatus('connecte')
  }, [])

  const logout = useCallback(async () => {
    await apiPost('/api/auth/logout/')
    setUser(null)
    setStatus('deconnecte')
  }, [])

  const value = useMemo(() => ({ status, user, login, logout }), [status, user, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
