import { useEffect, useState } from 'react'
import { useLocation } from 'react-router'
import { useApi } from '../hooks/useApi'

/** Pastille rouge du menu : nombre d'alertes à traiter (rafraîchie à chaque page). */
export function AlertBadge() {
  const { pathname } = useLocation()
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const refresh = () => setTick((value) => value + 1)
    window.addEventListener('alerts-changed', refresh)
    return () => window.removeEventListener('alerts-changed', refresh)
  }, [])

  const { data } = useApi<{ count: number }>(
    `/api/stocks/alerts/open-count/?page=${encodeURIComponent(pathname)}&v=${tick}`,
  )
  if (!data || data.count === 0) return null
  return (
    <span className="count-badge" aria-label={`${data.count} alerte(s) à traiter`}>
      {data.count}
    </span>
  )
}
