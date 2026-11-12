import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion'
import { pop } from '../anim'
import { Background } from '../components/Background'
import { Pill, Rise } from '../components/Text'
import { C, FONT } from '../theme'
import { SCENES, word } from '../timing'
import { Logo } from './Reponse'

const w = (index: number) => word('fin', index)
const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

/** 55,8 – 63 s : un projet personnel, et l'adresse du dépôt GitHub. */
export const Fin: React.FC = () => {
  const frame = useCurrentFrame()
  const g = SCENES.fin.from + frame
  const length = SCENES.fin.to - SCENES.fin.from
  const logo = pop(frame, 2, 200, 13)
  return (
    <AbsoluteFill style={{ color: C.white, fontFamily: FONT }}>
      <Background variant="green" globalFrame={g} />
      <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
        <div style={{ transform: `scale(${0.4 + 0.6 * logo})`, opacity: Math.min(1, logo * 2) }}>
          <Logo size={0.7} />
        </div>
        <Rise frame={frame} at={w(0)} style={{ marginTop: 60, fontSize: 50, fontWeight: 600, textAlign: 'center' }}>
          Un projet personnel, pour comprendre
          <br />
          la supply chain agroalimentaire
        </Rise>
        <Rise frame={frame} at={w(9)} style={{ marginTop: 50, fontSize: 40, fontWeight: 600, color: C.lime }}>
          Le code est sur GitHub
        </Rise>
        <Rise frame={frame} at={w(12)} style={{ marginTop: 18 }}>
          <Pill mono size={46} background={C.white} color={C.brandDark}>
            github.com/hsgnexio-cmd/erp-agro
          </Pill>
        </Rise>
        <Rise frame={frame} at={w(13) + 12} style={{ marginTop: 44, fontSize: 38, color: 'rgba(255,255,255,0.8)' }}>
          Nicolas Cloteaux · Django · React · PostgreSQL · Power BI
        </Rise>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: '#fff', opacity: interpolate(frame, [0, 6], [0.5, 0], CLAMP) }} />
      <AbsoluteFill
        style={{ background: '#000', opacity: interpolate(frame, [length - 18, length - 2], [0, 1], CLAMP) }}
      />
    </AbsoluteFill>
  )
}
