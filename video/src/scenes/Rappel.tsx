import React from 'react'
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from 'remotion'
import { pop } from '../anim'
import { Background } from '../components/Background'
import { Browser } from '../components/Browser'
import { Subtitles } from '../components/Subtitles'
import { Counter, Pill, Rise, Slam } from '../components/Text'
import { C, FONT, MONO } from '../theme'
import { SCENES, word } from '../timing'

const w = (index: number) => word('rappel', index)

const Stat: React.FC<{
  frame: number
  at: number
  value: number
  label: string
  detail: string
  detailAt?: number
  color?: string
}> = ({ frame, at, value, label, detail, detailAt, color = C.lime }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 30, marginTop: 18 }}>
    <Slam
      frame={frame}
      at={at}
      from={2}
      style={{ width: 200, textAlign: 'right', fontSize: 160, fontWeight: 900, lineHeight: 1, color }}
    >
      <Counter frame={frame} at={at} value={value} duration={10} />
    </Slam>
    <div>
      <Rise frame={frame} at={at + 3} style={{ fontSize: 52, fontWeight: 800, lineHeight: 1.05, whiteSpace: 'nowrap' }}>
        {label}
      </Rise>
      <Rise frame={frame} at={detailAt ?? at + 8} style={{ fontSize: 30, color: C.muted, marginTop: 6, whiteSpace: 'nowrap' }}>
        {detail}
      </Rise>
    </div>
  </div>
)

/** 20,1 – 29,5 s : le rappel. 23 lots identifiés, 8 bloqués, 6 enseignes à prévenir. */
export const Rappel: React.FC = () => {
  const frame = useCurrentFrame()
  const g = SCENES.rappel.from + frame
  const enter = pop(frame, 0, 120, 16)
  // La page défile sur les lots, puis saute aux clients livrés quand la voix en parle
  const scroll = interpolate(frame, [10, w(8) - 14, w(8) + 12, 281], [0, 1080, 2070, 2520], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.quad),
  })
  return (
    <AbsoluteFill style={{ color: C.white, fontFamily: FONT }}>
      <Background globalFrame={g} />
      <div
        style={{
          position: 'absolute',
          left: 800,
          top: 150,
          perspective: 2400,
          opacity: Math.min(1, enter * 1.6),
          transform: `translateX(${(1 - enter) * 300}px) scale(${1 + frame * 0.0002})`,
        }}
      >
        <Browser
          src="captures/rappel.jpg"
          width={1080}
          title="ERP Brévanne Traiteur · Rappel produit"
          scroll={scroll}
          sticky={248}
          style={{ transform: 'rotateY(-10deg) rotateX(3deg)', transformOrigin: '100% 50%' }}
        />
      </div>

      <div style={{ position: 'absolute', left: 80, top: 120, width: 700 }}>
        <Rise frame={frame} at={0} style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <Pill background={C.red} color={C.white} size={28}>
            RAPPEL PRODUIT
          </Pill>
          <span style={{ fontFamily: MONO, fontSize: 26, color: C.muted }}>lot LR-261109-0004</span>
        </Rise>
        <Stat frame={frame} at={w(0)} value={23} label="lots identifiés" detail="matières, semi-finis, produits finis" />
        <Stat
          frame={frame}
          at={w(3)}
          value={8}
          label="lots encore en stock"
          detail="bloqués automatiquement"
          detailAt={w(6)}
          color={C.red}
        />
        <Stat frame={frame} at={w(8)} value={6} label="enseignes à prévenir" detail="entrepôt par entrepôt" detailAt={w(11)} />
        <Rise frame={frame} at={w(12)} style={{ marginTop: 44, marginLeft: 4 }}>
          <Pill size={30}>Quantités exactes · liste prête pour Excel</Pill>
        </Rise>
      </div>
      <Subtitles id="rappel" />
    </AbsoluteFill>
  )
}
