import { useEffect, useState } from 'react'
import { apiGet } from '../api/client'

interface State<T> {
  path: string | null
  data?: T
  error?: string
}

/** Charge des données depuis l'API. Passer `null` pour ne rien charger. */
export function useApi<T>(path: string | null) {
  const [state, setState] = useState<State<T>>({ path: null })

  useEffect(() => {
    if (path === null) return
    let cancelled = false
    apiGet<T>(path)
      .then((data) => {
        if (!cancelled) setState({ path, data })
      })
      .catch((error: Error) => {
        if (!cancelled) setState({ path, error: error.message })
      })
    return () => {
      cancelled = true
    }
  }, [path])

  const isCurrent = state.path === path
  return {
    data: isCurrent ? state.data : undefined,
    error: isCurrent ? state.error : undefined,
    loading: path !== null && !isCurrent,
  }
}
