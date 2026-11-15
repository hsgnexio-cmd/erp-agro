import React from 'react'
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from 'remotion'
import { glide } from '../anim'
import { C, FONT } from '../theme'
import { CARTON } from '../timing'

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic) } as const
/** Images de recouvrement avant et après le carton (il glisse par-dessus les scènes). */
export const WIPE = 7

/** Carton de titre d'un acte : respiration d'une seconde, vert forêt et texte crème. */
export const Carton: React.FC<{ number: number; title: string; subtitle: string; first?: boolean }> = ({
  number,
  title,
  subtitle,
  first,
}) => {
  const frame = useCurrentFrame() - WIPE
  // Entre par le bas, repart par le haut
  const enter = first ? 0 : interpolate(frame, [-WIPE, 0], [100, 0], CLAMP)
  const leave = interpolate(frame, [CARTON - 1, CARTON + WIPE - 1], [0, 100], CLAMP)
  const line = interpolate(frame, [2, 16], [0, 1], CLAMP)
  return (
    <AbsoluteFill
      style={{
        background: C.forest,
        color: C.cream,
        fontFamily: FONT,
        clipPath: `inset(${enter}% 0 ${leave}% 0)`,
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          fontSize: 30,
          fontWeight: 600,
          letterSpacing: '0.34em',
          textIndent: '0.34em',
          color: C.accent,
          opacity: glide(frame, 0, 8),
        }}
      >
        ACTE {number}
      </div>
      <div
        style={{
          marginTop: 22,
          fontSize: 104,
          fontWeight: 700,
          lineHeight: 1.05,
          maxWidth: 1600,
          opacity: glide(frame, 2, 8),
          transform: `translateY(${(1 - glide(frame, 2, 12)) * 26}px)`,
        }}
      >
        {title}
      </div>
      <div style={{ marginTop: 34, width: 120 * line, height: 3, borderRadius: 2, background: C.accent }} />
      <div style={{ marginTop: 30, fontSize: 40, fontWeight: 500, color: 'rgba(247,240,220,0.82)', opacity: glide(frame, 6, 8) }}>
        {subtitle}
      </div>
    </AbsoluteFill>
  )
}
