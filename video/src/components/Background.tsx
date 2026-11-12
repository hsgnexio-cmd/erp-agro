import React from 'react'
import { AbsoluteFill } from 'remotion'
import { C } from '../theme'
import { pulse } from '../timing'

type Variant = 'night' | 'green' | 'alert'

const BASE: Record<Variant, string> = {
  night: `radial-gradient(120% 90% at 20% 10%, ${C.deep} 0%, ${C.night} 70%)`,
  green: `radial-gradient(110% 100% at 30% 20%, #3b8448 0%, ${C.brand} 38%, ${C.brandDark} 100%)`,
  alert: 'radial-gradient(120% 90% at 50% 40%, #1a0a0a 0%, #050505 75%)',
}

/** Fond animé : lueurs qui dérivent, grille fine et légère pulsation sur les temps. */
export const Background: React.FC<{ variant?: Variant; globalFrame: number }> = ({
  variant = 'night',
  globalFrame,
}) => {
  const t = globalFrame / 30
  const p = pulse(globalFrame)
  const glow = variant === 'alert' ? C.red : C.lime
  // Battement de cœur pour la scène d'alerte
  const heart = variant === 'alert' ? Math.pow(Math.max(0, Math.sin(t * 4.2)), 6) : 0
  const grid = 'rgba(255,255,255,0.05)'
  return (
    <AbsoluteFill style={{ background: BASE[variant] }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(600px 600px at ${30 + 12 * Math.sin(t * 0.5)}% ${
            35 + 10 * Math.cos(t * 0.4)
          }%, ${glow}${variant === 'alert' ? '22' : '26'} 0%, transparent 70%)`,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(700px 700px at ${75 + 10 * Math.cos(t * 0.45)}% ${
            70 + 8 * Math.sin(t * 0.6)
          }%, ${variant === 'green' ? '#ffffff14' : `${C.brand}55`} 0%, transparent 70%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${grid} 1px, transparent 1px), linear-gradient(90deg, ${grid} 1px, transparent 1px)`,
          backgroundSize: '96px 96px',
          backgroundPosition: `${-t * 14}px ${-t * 8}px`,
          maskImage: 'radial-gradient(80% 80% at 50% 50%, black 30%, transparent 100%)',
          WebkitMaskImage: 'radial-gradient(80% 80% at 50% 50%, black 30%, transparent 100%)',
        }}
      />
      {variant === 'alert' ? (
        <AbsoluteFill
          style={{
            boxShadow: `inset 0 0 ${260 + heart * 120}px ${40 + heart * 60}px rgba(255,40,40,${
              0.16 + heart * 0.22
            })`,
          }}
        />
      ) : (
        <AbsoluteFill style={{ background: `rgba(255,255,255,${p * 0.05})` }} />
      )}
    </AbsoluteFill>
  )
}
