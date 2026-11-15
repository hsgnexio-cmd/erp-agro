import type { ReactNode } from 'react'

/** Charge d'une journée par rapport à la capacité de la ligne : verte, orange à 85 %, rouge au-delà. */
export function LoadBar({ hours, capacity, children }: { hours: number; capacity: number; children: ReactNode }) {
  const rate = capacity > 0 ? (hours / capacity) * 100 : 0
  const tone = rate > 100 ? 'danger' : rate >= 85 ? 'warn' : 'ok'
  return (
    <div className="planning-load">
      <div className="load-text">
        <span>{children}</span>
        <span className={`load-rate load-text-${tone}`}>{Math.round(rate)} %</span>
      </div>
      <div className="load-track" aria-hidden="true">
        <span className={`load-fill load-${tone}`} style={{ width: `${Math.min(100, rate)}%` }} />
      </div>
    </div>
  )
}
