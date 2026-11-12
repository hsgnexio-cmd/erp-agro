import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion'
import { lerp, pop } from '../anim'
import { Background } from '../components/Background'
import { Pill, Rise, Slam } from '../components/Text'
import { C, FONT } from '../theme'
import { SCENES, word } from '../timing'

const w = (index: number) => word('reponse', index)
const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

/** Le logotype « ERP Brévanne Traiteur », réutilisé à la fin. */
export const Logo: React.FC<{ size?: number }> = ({ size = 1 }) => (
  <div style={{ fontFamily: FONT, color: C.white, textAlign: 'center', lineHeight: 1 }}>
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 34 * size }}>
      <div
        style={{
          fontWeight: 900,
          fontSize: 92 * size,
          padding: `${14 * size}px ${30 * size}px`,
          borderRadius: 26 * size,
          background: C.lime,
          color: C.brandDark,
        }}
      >
        ERP
      </div>
      <div style={{ fontWeight: 900, fontSize: 190 * size, letterSpacing: '-0.02em' }}>Brévanne</div>
    </div>
    <div
      style={{
        marginTop: 22 * size,
        fontWeight: 600,
        fontSize: 44 * size,
        letterSpacing: '0.62em',
        marginRight: '-0.62em',
        color: C.lime,
      }}
    >
      TRAITEUR
    </div>
  </div>
)

/** 7 – 11,7 s : le drop. « Voici un projet personnel : un ERP agroalimentaire complet. » */
export const Reponse: React.FC = () => {
  const frame = useCurrentFrame()
  const g = SCENES.reponse.from + frame
  const logo = pop(frame, 0, 240, 13)
  // Le logo remonte pour laisser la place à la présentation du projet
  const up = lerp(frame, [w(1) - 6, w(1) + 10], [0, 1])
  const line = interpolate(frame, [w(5) + 6, w(5) + 20], [0, 1], CLAMP)
  return (
    <AbsoluteFill style={{ color: C.white }}>
      <Background variant="green" globalFrame={g} />
      {/* Ondes de choc du drop */}
      {[0, 7, 14].map((delay) => {
        const p = interpolate(frame, [delay, delay + 34], [0, 1], CLAMP)
        return (
          <AbsoluteFill key={delay} style={{ alignItems: 'center', justifyContent: 'center' }}>
            <div
              style={{
                width: 500,
                height: 500,
                borderRadius: '50%',
                border: `6px solid ${C.lime}`,
                opacity: (1 - p) * 0.7,
                transform: `scale(${0.2 + p * 4.2})`,
              }}
            />
          </AbsoluteFill>
        )
      })}
      <AbsoluteFill style={{ background: '#ffffff', opacity: interpolate(frame, [0, 8], [0.85, 0], CLAMP) }} />

      <AbsoluteFill
        style={{
          alignItems: 'center',
          justifyContent: 'center',
          transform: `translateY(${-250 * up}px) scale(${(0.3 + 0.7 * logo) * (1 - 0.42 * up)})`,
        }}
      >
        <Logo />
      </AbsoluteFill>

      <AbsoluteFill style={{ alignItems: 'center', top: 470, fontFamily: FONT }}>
        <Rise frame={frame} at={w(1)} style={{ fontSize: 66, fontWeight: 600 }}>
          Un projet personnel
        </Rise>
        <div style={{ position: 'relative', marginTop: 6 }}>
          <Slam frame={frame} at={w(5)} style={{ fontSize: 160, fontWeight: 900, color: C.lime, lineHeight: 1.1 }}>
            ERP agroalimentaire
          </Slam>
          <div
            style={{
              position: 'absolute',
              left: 0,
              bottom: -14,
              height: 12,
              borderRadius: 6,
              width: `${line * 100}%`,
              background: C.white,
            }}
          />
        </div>
        <Rise frame={frame} at={w(7) + 6} style={{ marginTop: 44 }}>
          <Pill background="rgba(6,18,10,0.55)" color={C.white} size={34}>
            conçu et construit seul, de A à Z
          </Pill>
        </Rise>
      </AbsoluteFill>
    </AbsoluteFill>
  )
}
