import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion'
import { pop } from '../anim'
import { Background } from '../components/Background'
import { Counter, Rise, Slam, Words } from '../components/Text'
import { C, FONT } from '../theme'
import { SCENES, word } from '../timing'

const w = (index: number) => word('preuves', index)
const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const
const TECH = ['Django', 'React', 'PostgreSQL', 'Docker', 'Power BI']

/** Un chiffre géant à gauche, sa preuve à droite. */
const Panel: React.FC<{
  frame: number
  from: number
  to: number
  green?: boolean
  number: React.ReactNode
  ghost: string
  children: React.ReactNode
}> = ({ frame, from, to, green, number, ghost, children }) => {
  if (frame < from || frame >= to) return null
  const local = frame - from
  const out = interpolate(frame, [to - 5, to], [0, 1], CLAMP)
  const accent = green ? C.white : C.lime
  return (
    <AbsoluteFill style={{ transform: `translateX(${-out * 100}%)` }}>
      <Background variant={green ? 'green' : 'night'} globalFrame={SCENES.preuves.from + frame} />
      {/* Chiffre fantôme, en contour, qui dérive derrière */}
      <div
        style={{
          position: 'absolute',
          right: -60 + local * 1.2,
          top: -140,
          fontFamily: FONT,
          fontWeight: 900,
          fontSize: 1100,
          lineHeight: 1,
          color: 'transparent',
          WebkitTextStroke: `4px rgba(255,255,255,${green ? 0.16 : 0.08})`,
        }}
      >
        {ghost}
      </div>
      <AbsoluteFill style={{ flexDirection: 'row', alignItems: 'center', padding: '0 110px', gap: 70 }}>
        <Slam frame={local} at={1} from={2.8} style={{ fontSize: 440, fontWeight: 900, lineHeight: 1, color: accent }}>
          {number}
        </Slam>
        <div style={{ flex: 1 }}>{children}</div>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: '#fff', opacity: interpolate(local, [0, 5], [0.45, 0], CLAMP) }} />
    </AbsoluteFill>
  )
}

/** 46,4 – 55,8 s : 12 règles métier, 470 tests, zéro stock sans mouvement. */
export const Preuves: React.FC = () => {
  const frame = useCurrentFrame()
  const g = SCENES.preuves.from + frame
  const second = w(7) - 3
  const third = w(14) - 3
  const tech = 254
  const title: React.CSSProperties = { fontSize: 128, fontWeight: 900, lineHeight: 1.02 }
  const detail: React.CSSProperties = { fontSize: 56, fontWeight: 600, color: C.muted, marginTop: 18 }
  return (
    <AbsoluteFill style={{ color: C.white, fontFamily: FONT }}>
      <Background globalFrame={g} />
      <Panel frame={frame} from={0} to={second} green number="12" ghost="12">
        <Rise frame={frame} at={w(1)} style={title}>
          règles métier
        </Rise>
        <Rise frame={frame} at={w(3)} style={{ ...detail, color: C.white }}>
          garanties par le serveur,
          <br />
          pas seulement par l'écran
        </Rise>
      </Panel>
      <Panel
        frame={frame}
        from={second}
        to={third}
        ghost="470"
        number={<Counter frame={frame} at={w(9) - 2} value={470} duration={w(11) + 8 - w(9)} suffix="+" />}
      >
        <Rise frame={frame} at={w(12)} style={title}>
          tests
          <br />
          automatiques
        </Rise>
        <Rise frame={frame} at={w(13) + 6} style={detail}>
          relancés à chaque modification
        </Rise>
      </Panel>
      <Panel frame={frame} from={third} to={tech + 5} green number="0" ghost="0">
        <Words
          frame={frame}
          style={title}
          words={[
            { text: 'stock', at: w(15) },
            { text: 'sans', at: w(16) },
            { text: 'mouvement', at: w(17) },
            { text: 'tracé', at: w(18) },
          ]}
        />
        <Rise frame={frame} at={w(18) + 8} style={{ ...detail, color: C.white }}>
          qui, quand, quoi, pourquoi
        </Rise>
      </Panel>
      {frame >= tech ? (
        <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', gap: 26, flexDirection: 'row' }}>
          {TECH.map((name, index) => (
            <div
              key={name}
              style={{
                transform: `scale(${pop(frame, tech + 2 + index * 3, 240, 13)})`,
                padding: '22px 38px',
                borderRadius: 70,
                fontSize: 50,
                fontWeight: 800,
                border: `3px solid ${C.lime}`,
                background: 'rgba(255,255,255,0.07)',
              }}
            >
              {name}
            </div>
          ))}
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  )
}
