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

/** 55,8 – 62 s : le logo et l'adresse du dépôt GitHub. */
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
          <Logo size={0.9} />
        </div>
        <Rise frame={frame} at={w(3)} style={{ marginTop: 90, fontSize: 54, fontWeight: 600 }}>
          Le code est sur GitHub
        </Rise>
        <Rise frame={frame} at={w(7)} style={{ marginTop: 26 }}>
          <Pill mono size={46} background={C.white} color={C.brandDark}>
            github.com/hsgnexio-cmd/erp-agro
          </Pill>
        </Rise>
        <Rise frame={frame} at={w(7) + 22} style={{ marginTop: 56, fontSize: 38, color: 'rgba(255,255,255,0.8)' }}>
          Un projet de Nicolas Cloteaux · Django · React · PostgreSQL · Power BI
        </Rise>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: '#fff', opacity: interpolate(frame, [0, 6], [0.5, 0], CLAMP) }} />
      <AbsoluteFill
        style={{ background: '#000', opacity: interpolate(frame, [length - 18, length - 2], [0, 1], CLAMP) }}
      />
    </AbsoluteFill>
  )
}
