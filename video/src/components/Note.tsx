import React from 'react'
import { glide, pop } from '../anim'
import { C, FONT, MONO } from '../theme'

/**
 * Étiquette posée sur l'image (hors caméra) : un titre court et, si besoin, une ligne de détail.
 * Largeur bornée et texte sur une ligne : elle ne peut pas déborder de l'image.
 */
export const Note: React.FC<{
  frame: number
  from: number
  to: number
  /** Coin de l'image où l'étiquette s'accroche. */
  corner?: 'top-left' | 'top-right'
  label: string
  title: string
  detail?: string
  mono?: boolean
  tone?: 'forest' | 'red'
}> = ({ frame, from, to, corner = 'top-right', label, title, detail, mono, tone = 'forest' }) => {
  if (frame < from || frame > to) return null
  const enter = pop(frame, from)
  const opacity = Math.min(glide(frame, from, 6), 1 - glide(frame, to - 8, 8))
  const color = tone === 'red' ? C.red : C.forest
  return (
    <div
      style={{
        position: 'absolute',
        top: 64,
        [corner === 'top-right' ? 'right' : 'left']: 56,
        maxWidth: 900,
        opacity,
        transform: `translateY(${(1 - enter) * -18}px)`,
        padding: '18px 26px 20px',
        borderRadius: 16,
        background: C.white,
        borderLeft: `6px solid ${color}`,
        boxShadow: '0 2px 6px rgba(16,58,34,0.08), 0 18px 44px rgba(16,58,34,0.2)',
        fontFamily: FONT,
        whiteSpace: 'nowrap',
      }}
    >
      <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '0.14em', color }}>{label.toUpperCase()}</div>
      <div style={{ marginTop: 6, fontSize: 34, fontWeight: 700, color: C.ink, fontFamily: mono ? MONO : FONT }}>{title}</div>
      {detail ? <div style={{ marginTop: 4, fontSize: 24, fontWeight: 500, color: C.muted }}>{detail}</div> : null}
    </div>
  )
}
