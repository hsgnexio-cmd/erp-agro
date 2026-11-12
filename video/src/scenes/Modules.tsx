import React from 'react'
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from 'remotion'
import { lerp, pop } from '../anim'
import { Background } from '../components/Background'
import { Rise, Slam, Words } from '../components/Text'
import { C, FONT } from '../theme'
import { SCENES, word } from '../timing'

const w = (index: number) => word('modules', index)
const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

const WALL = [
  'achats', 'lots', 'tableau-de-bord', 'stocks', 'production',
  'plan-production', 'planning', 'rappel', 'trs', 'ventes',
  'expeditions', 'previsions', 'tracabilite', 'taux-de-service', 'temperatures',
]
const CUTS = [
  { label: 'Achats', src: 'achats', detail: 'commandes, réceptions, contrôles' },
  { label: 'Stocks', src: 'stocks', detail: 'lots, DLC, FEFO, chaîne du froid' },
  { label: 'Production', src: 'production', detail: 'ordres de fabrication, rendements, TRS' },
  { label: 'Ventes', src: 'ventes', detail: 'EDI, préparation, expédition' },
  { label: 'Prévisions', src: 'previsions', detail: 'promotions, plan de production, MRP' },
]
const TILE = { width: 560, height: 350, gap: 30 }

/** Mur de captures en perspective : « un écran parmi quarante ». */
const Wall: React.FC<{ frame: number }> = ({ frame }) => {
  const zoom = lerp(frame, [0, 74], [2.5, 1.02])
  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', perspective: 1900 }}>
      <div
        style={{
          width: 5 * TILE.width + 4 * TILE.gap,
          display: 'flex',
          flexWrap: 'wrap',
          gap: TILE.gap,
          transform: `rotateX(24deg) rotateZ(-7deg) scale(${zoom}) translate(${-frame * 0.8}px, ${frame * 0.3}px)`,
        }}
      >
        {WALL.map((name, index) => (
          <div
            key={name}
            style={{
              width: TILE.width,
              height: TILE.height,
              overflow: 'hidden',
              borderRadius: 18,
              boxShadow: '0 30px 60px rgba(0,0,0,0.5)',
              opacity: interpolate(frame, [index * 1.5, index * 1.5 + 8], [0, 1], CLAMP),
            }}
          >
            <Img src={staticFile(`captures/${name}.jpg`)} style={{ width: '100%', display: 'block' }} />
          </div>
        ))}
      </div>
    </AbsoluteFill>
  )
}

/** Plan plein écran d'un module, avec son nom en très grand. */
const Cut: React.FC<{ frame: number; from: number; index: number }> = ({ frame, from, index }) => {
  const local = frame - from
  const cut = CUTS[index]
  const slide = interpolate(local, [0, 5], [1, 0], CLAMP)
  return (
    <AbsoluteFill style={{ transform: `translateX(${slide * 100}%) skewX(${-slide * 8}deg)`, overflow: 'hidden' }}>
      <Img
        src={staticFile(`captures/${cut.src}.jpg`)}
        style={{ width: '100%', transform: `scale(${1.1 - local * 0.003})`, transformOrigin: '50% 30%' }}
      />
      <AbsoluteFill
        style={{ background: 'linear-gradient(180deg, rgba(6,18,10,0.1) 30%, rgba(6,18,10,0.94) 82%)' }}
      />
      <div style={{ position: 'absolute', left: 90, bottom: 80, fontFamily: FONT, color: C.white }}>
        <div style={{ fontSize: 40, fontWeight: 800, color: C.lime, letterSpacing: '0.12em' }}>
          0{index + 1} / 05
        </div>
        <Slam frame={local} at={1} from={1.5} style={{ fontSize: 230, fontWeight: 900, lineHeight: 1, transformOrigin: '0 100%' }}>
          {cut.label}
        </Slam>
        <div style={{ fontSize: 44, fontWeight: 600, color: C.muted, marginTop: 4 }}>{cut.detail}</div>
      </div>
      <AbsoluteFill style={{ background: '#fff', opacity: interpolate(local, [0, 4], [0.5, 0], CLAMP) }} />
    </AbsoluteFill>
  )
}

/** 29,5 – 38,9 s : « un écran parmi quarante », les cinq modules, puis « un seul outil ». */
export const Modules: React.FC = () => {
  const frame = useCurrentFrame()
  const g = SCENES.modules.from + frame
  const cuts = CUTS.map((_, index) => w(7 + index) - 2)
  const outro = w(12) - 3
  const current = cuts.findLastIndex((at) => frame >= at)
  return (
    <AbsoluteFill style={{ color: C.white, fontFamily: FONT }}>
      <Background globalFrame={g} />
      {frame < cuts[0] + 6 ? (
        <>
          <Wall frame={frame} />
          <AbsoluteFill style={{ background: 'radial-gradient(60% 60% at 50% 50%, rgba(6,18,10,0.82) 0%, rgba(6,18,10,0.35) 100%)' }} />
          <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
            <Rise frame={frame} at={w(3)} style={{ fontSize: 96, fontWeight: 800 }}>
              Un écran parmi
            </Rise>
            <Slam frame={frame} at={w(6)} from={3} style={{ fontSize: 420, fontWeight: 900, color: C.lime, lineHeight: 0.95 }}>
              40
            </Slam>
          </AbsoluteFill>
        </>
      ) : null}
      {frame < outro + 6
        ? cuts.map((at, index) =>
            index <= current && index >= current - 1 ? <Cut key={index} frame={frame} from={at} index={index} /> : null,
          )
        : null}
      {frame >= outro ? (
        <AbsoluteFill
          style={{ transform: `translateY(${interpolate(frame, [outro, outro + 6], [100, 0], CLAMP)}%)` }}
        >
          <Background globalFrame={g} />
          <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
            <Words
              frame={frame}
              style={{ fontSize: 84, fontWeight: 800, justifyContent: 'center' }}
              words={[
                { text: 'Tout', at: w(12) },
                { text: 'le', at: w(13) },
                { text: 'cycle', at: w(14) },
                { text: "d'un", at: w(15) },
                { text: 'industriel', at: w(16) },
                { text: 'du', at: w(17) },
                { text: 'frais', at: w(18) },
              ]}
            />
            <div style={{ display: 'flex', alignItems: 'center', marginTop: 90 }}>
              {CUTS.map((cut, index) => {
                const at = outro + 8 + index * 5
                const p = pop(frame, at, 220, 14)
                return (
                  <React.Fragment key={cut.label}>
                    {index > 0 ? (
                      <div
                        style={{
                          height: 6,
                          width: 56 * interpolate(frame, [at - 4, at], [0, 1], CLAMP),
                          background: C.lime,
                        }}
                      />
                    ) : null}
                    <div
                      style={{
                        transform: `scale(${p})`,
                        padding: '22px 38px',
                        borderRadius: 60,
                        fontSize: 46,
                        fontWeight: 800,
                        background: 'rgba(255,255,255,0.08)',
                        border: `3px solid ${C.lime}`,
                      }}
                    >
                      {cut.label}
                    </div>
                  </React.Fragment>
                )
              })}
            </div>
            <div style={{ marginTop: 80 }}>
              <Slam frame={frame} at={w(20)} style={{ fontSize: 190, fontWeight: 900, color: C.lime, lineHeight: 1 }}>
                Un seul outil.
              </Slam>
            </div>
          </AbsoluteFill>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  )
}
