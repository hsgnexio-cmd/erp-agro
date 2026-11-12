import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion'
import { lerp, pop, visible } from '../anim'
import { Background } from '../components/Background'
import { Browser } from '../components/Browser'
import { Subtitles } from '../components/Subtitles'
import { Pill, Rise, Slam } from '../components/Text'
import { C, FONT } from '../theme'
import { SCENES, word } from '../timing'

const w = (index: number) => word('tracabilite', index)
const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const
const TYPED = 14 // caractères du numéro de lot (images trace-00 à trace-14)

const Arrow: React.FC<{ up?: boolean }> = ({ up }) => (
  <svg width="74" height="74" viewBox="0 0 74 74" style={{ transform: up ? undefined : 'rotate(180deg)' }}>
    <circle cx="37" cy="37" r="37" fill={C.lime} />
    <path d="M37 56 V22 M22 35 L37 20 L52 35" stroke={C.brandDark} strokeWidth="7" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

/** 11,7 – 20,1 s : un numéro de lot, un clic, et l'arbre de traçabilité se déroule. */
export const Tracabilite: React.FC = () => {
  const frame = useCurrentFrame()
  const g = SCENES.tracabilite.from + frame
  const enter = pop(frame, 0, 120, 16)
  const click = w(5)
  const result = click + 4
  // Saisie du numéro de lot, caractère par caractère, pendant « un numéro de lot »
  const typed = Math.round(interpolate(frame, [w(0), w(4) - 4], [0, TYPED], CLAMP))
  const src =
    frame < result ? `captures/trace-${String(typed).padStart(2, '0')}.jpg` : 'captures/tracabilite.jpg'
  // Gros plan sur le champ pendant la saisie, puis sur l'arbre « aval » une fois tracé
  const zoom = frame < result ? 1.9 : lerp(frame, [result + 4, result + 40], [1, 1.42])
  const focus: [number, number] = frame < result ? [0.1, 0.3] : [0.95, 0.3]
  const scroll = frame < result ? 0 : lerp(frame, [w(9), 250], [0, 980], false)
  // Curseur : va jusqu'au bouton « Tracer » et clique
  const cx = lerp(frame, [w(4) - 14, click - 1], [760, 364])
  const cy = lerp(frame, [w(4) - 14, click - 1], [560, 283])
  const ripple = interpolate(frame, [click, click + 10], [0, 1], CLAMP)
  const first = visible(frame, 0, w(6) - 4, 6)
  const second = visible(frame, w(6) - 4, 400, 6)
  const row: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: 26, marginTop: 38 }
  return (
    <AbsoluteFill style={{ color: C.white, fontFamily: FONT }}>
      <Background globalFrame={g} />
      <div
        style={{
          position: 'absolute',
          left: 60,
          top: 130,
          perspective: 2400,
          opacity: Math.min(1, enter * 1.6),
          transform: `translateY(${(1 - enter) * 260}px) scale(${1 + frame * 0.00022})`,
        }}
      >
        <Browser
          src={src}
          width={1210}
          title="ERP Brévanne Traiteur · Traçabilité"
          zoom={zoom}
          focus={focus}
          scroll={scroll}
          style={{ transform: 'rotateY(10deg) rotateX(3deg)', transformOrigin: '0% 50%' }}
        >
          {frame < result + 2 ? (
            <>
              <div
                style={{
                  position: 'absolute',
                  left: 364 - 60,
                  top: 283 - 60,
                  width: 120,
                  height: 120,
                  borderRadius: '50%',
                  border: `5px solid ${C.brand}`,
                  opacity: frame >= click ? 1 - ripple : 0,
                  transform: `scale(${0.2 + ripple})`,
                }}
              />
              <svg
                width="44"
                height="44"
                viewBox="0 0 24 24"
                style={{ position: 'absolute', left: cx, top: cy, opacity: frame > w(4) - 16 ? 1 : 0 }}
              >
                <path d="M4 2 L4 19 L8.5 15 L11.5 22 L14.5 20.8 L11.6 14 L18 14 Z" fill="#111" stroke="#fff" strokeWidth="1.4" />
              </svg>
            </>
          ) : null}
        </Browser>
      </div>

      <div style={{ position: 'absolute', left: 1320, top: 250, width: 540, opacity: first }}>
        <Rise frame={frame} at={w(0)} style={{ fontSize: 84, fontWeight: 800, lineHeight: 1.05 }}>
          1 numéro
          <br />
          de lot.
        </Rise>
        <div style={{ marginTop: 36 }}>
          <Slam frame={frame} at={w(4)} style={{ fontSize: 150, fontWeight: 900, color: C.lime, lineHeight: 1 }}>
            1 clic.
          </Slam>
        </div>
      </div>

      <div style={{ position: 'absolute', left: 1320, top: 200, width: 560, opacity: second }}>
        <Rise frame={frame} at={w(6)} style={{ fontSize: 30, fontWeight: 800, letterSpacing: '0.2em', color: C.lime }}>
          TRAÇABILITÉ TOTALE
        </Rise>
        <Rise frame={frame} at={w(8)} style={row}>
          <Arrow up />
          <div>
            <div style={{ fontSize: 76, fontWeight: 900, lineHeight: 1 }}>Amont</div>
            <div style={{ fontSize: 36, color: C.muted, marginTop: 6 }}>chaque matière</div>
          </div>
        </Rise>
        <Rise frame={frame} at={w(12)} style={row}>
          <Arrow />
          <div>
            <div style={{ fontSize: 76, fontWeight: 900, lineHeight: 1 }}>Aval</div>
            <div style={{ fontSize: 36, color: C.muted, marginTop: 6 }}>chaque produit</div>
          </div>
        </Rise>
        <Rise frame={frame} at={w(15)} style={{ marginTop: 50 }}>
          <Pill size={29}>jusqu'aux entrepôts des enseignes</Pill>
        </Rise>
      </div>
      <Subtitles id="tracabilite" />
    </AbsoluteFill>
  )
}
