import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion'
import { lerp, pop, visible } from '../anim'
import { Background } from '../components/Background'
import { Browser } from '../components/Browser'
import { Subtitles } from '../components/Subtitles'
import { Pill, Rise, Slam } from '../components/Text'
import { C, FONT } from '../theme'
import { SCENES, word } from '../timing'

const w = (index: number) => word('pilotage', index)
const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

const ROLES = [
  { src: 'tableau-qualite', role: 'Qualité', who: 'Claire', count: '3 indicateurs', x: -610, tilt: 16 },
  { src: 'tableau-de-bord', role: 'Direction', who: 'Hélène', count: '9 indicateurs', x: 0, tilt: 0 },
  { src: 'tableau-commercial', role: 'Commercial', who: 'Thomas', count: '2 indicateurs', x: 610, tilt: -16 },
]

/** 38,9 – 46,4 s : le tableau de bord, puis une vue par métier. */
export const Pilotage: React.FC = () => {
  const frame = useCurrentFrame()
  const g = SCENES.pilotage.from + frame
  const split = w(7) - 5
  const enter = pop(frame, 0, 120, 16)
  const first = visible(frame, -10, split + 4, 5)
  const scroll = interpolate(frame, [6, w(3), split], [330, 640, 1260], CLAMP)
  return (
    <AbsoluteFill style={{ color: C.white, fontFamily: FONT }}>
      <Background globalFrame={g} />

      {/* Premier temps : le tableau de bord de la direction */}
      <AbsoluteFill style={{ opacity: first }}>
        <div
          style={{
            position: 'absolute',
            left: 470,
            top: 96,
            perspective: 2400,
            transform: `translateY(${(1 - enter) * 240}px) scale(${1 + frame * 0.0003})`,
          }}
        >
          <Browser
            src="captures/tableau-de-bord.jpg"
            width={1370}
            title="ERP Brévanne Traiteur · Tableau de bord"
            scroll={scroll}
            style={{ transform: 'rotateY(-8deg) rotateX(4deg)', transformOrigin: '100% 50%' }}
          />
        </div>
        <div style={{ position: 'absolute', left: 80, top: 210, width: 420 }}>
          <Slam frame={frame} at={w(0)} from={2.6} style={{ fontSize: 400, fontWeight: 900, color: C.lime, lineHeight: 0.9 }}>
            9
          </Slam>
          <Rise frame={frame} at={w(1)} style={{ fontSize: 74, fontWeight: 800, lineHeight: 1.05, marginTop: 10 }}>
            indicateurs
            <br />
            clés
          </Rise>
          <Rise frame={frame} at={w(3)} style={{ marginTop: 40 }}>
            <Pill size={30}>semaine après semaine</Pill>
          </Rise>
        </div>
      </AbsoluteFill>

      {/* Second temps : chaque rôle a son tableau de bord */}
      {frame >= split ? (
        <AbsoluteFill>
          <AbsoluteFill style={{ alignItems: 'center', top: 70 }}>
            <Rise frame={frame} at={w(8)} style={{ fontSize: 80, fontWeight: 800 }}>
              Chaque métier voit <span style={{ color: C.lime }}>son métier</span>.
            </Rise>
          </AbsoluteFill>
          {ROLES.map((item, index) => {
            const at = split + [5, 0, 10][index]
            const p = pop(frame, at, 150, 15)
            const center = index === 1
            const width = center ? 800 : 640
            return (
              <div
                key={item.role}
                style={{
                  position: 'absolute',
                  left: 960 + item.x - width / 2,
                  top: center ? 250 : 320,
                  width,
                  zIndex: center ? 2 : 1,
                  perspective: 1800,
                  opacity: Math.min(1, p * 1.5),
                  transform: `translateY(${(1 - p) * 300}px)`,
                }}
              >
                <Browser
                  src={`captures/${item.src}.jpg`}
                  width={width}
                  title={`${item.who} · ${item.role}`}
                  scroll={lerp(frame, [split, 225], [center ? 240 : 150, center ? 330 : 190], false)}
                  style={{ transform: `rotateY(${item.tilt}deg)` }}
                />
                <div style={{ display: 'flex', justifyContent: 'center', marginTop: 30 }}>
                  <Rise frame={frame} at={at + 10}>
                    <Pill size={center ? 34 : 28} background={center ? C.lime : 'rgba(255,255,255,0.12)'} color={center ? C.night : C.white}>
                      {item.role} · {item.count}
                    </Pill>
                  </Rise>
                </div>
              </div>
            )
          })}
        </AbsoluteFill>
      ) : null}
      <Subtitles id="pilotage" />
    </AbsoluteFill>
  )
}
