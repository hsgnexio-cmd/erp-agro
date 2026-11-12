import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion'
import { lerp, visible } from '../anim'
import { Background } from '../components/Background'
import { Pill, Rise, Slam, Words } from '../components/Text'
import { C, FONT, MONO } from '../theme'
import { SCENES, word } from '../timing'

const w = (index: number) => word('accroche', index)
const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

/** 0 – 7 s : l'alerte. « Un lot de crème est contaminé. Combien de produits ? Quels clients ? » */
export const Accroche: React.FC = () => {
  const frame = useCurrentFrame()
  const end = SCENES.accroche.to
  // Secousse au moment où tombe « contaminé »
  const hit = w(5)
  const shake = frame >= hit ? Math.exp(-(frame - hit) / 5) : 0
  const dx = Math.sin(frame * 2.3) * 22 * shake
  const dy = Math.cos(frame * 3.1) * 14 * shake
  const flash = interpolate(frame, [hit, hit + 2, hit + 9], [0, 0.5, 0], CLAMP)
  // Les trois temps de l'accroche
  const a = visible(frame, 0, w(6) - 4, 5)
  const b = visible(frame, w(6) - 4, w(11) - 4, 5)
  const c = visible(frame, w(11) - 4, end + 20, 5)
  // Juste avant le drop : tout grossit, puis un cercle vert envahit l'écran
  const rush = lerp(frame, [end - 14, end], [0, 1])
  const big: React.CSSProperties = { fontFamily: FONT, fontWeight: 800, fontSize: 132, lineHeight: 1.08 }
  const center: React.CSSProperties = {
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'column',
    textAlign: 'center',
  }
  return (
    <AbsoluteFill style={{ color: C.white }}>
      <Background variant="alert" globalFrame={frame} />
      <AbsoluteFill style={{ transform: `translate(${dx}px, ${dy}px) scale(${1 + frame * 0.0004 + rush * 0.5})` }}>
        <div style={{ position: 'absolute', top: 70, left: 90, display: 'flex', gap: 22, alignItems: 'center' }}>
          <Pill background={C.red} color={C.white} size={28}>
            <span style={{ opacity: Math.floor(frame / 9) % 2 ? 0.35 : 1 }}>●</span> ALERTE FOURNISSEUR
          </Pill>
          <Rise frame={frame} at={w(5) + 12} style={{ fontFamily: MONO, fontSize: 28, color: C.muted }}>
            Lot LR-261109-0004 · Crème fraîche 35 % MG
          </Rise>
        </div>

        <AbsoluteFill style={{ ...center, opacity: a }}>
          <Rise frame={frame} at={w(0) - 2} style={big}>
            Un lot de crème est
          </Rise>
          <Slam frame={frame} at={hit} from={3.2} style={{ ...big, fontWeight: 900, fontSize: 230, color: C.red }}>
            CONTAMINÉ
          </Slam>
        </AbsoluteFill>

        <AbsoluteFill style={{ ...center, opacity: b }}>
          <Words
            frame={frame}
            style={{ ...big, justifyContent: 'center', maxWidth: 1500 }}
            words={[
              { text: 'Combien', at: w(6) },
              { text: 'de', at: w(7) },
              { text: 'produits', at: w(8) },
              { text: 'sont', at: w(9) },
              { text: 'touchés', at: w(10), color: C.red },
              { text: '?', at: w(10) + 4, color: C.red },
            ]}
          />
        </AbsoluteFill>

        <AbsoluteFill style={{ ...center, opacity: c * (1 - rush) }}>
          <Words
            frame={frame}
            style={{ ...big, justifyContent: 'center', maxWidth: 1500 }}
            words={[
              { text: 'Quels', at: w(11) },
              { text: 'clients', at: w(12) },
              { text: 'ont', at: w(13) },
              { text: 'été', at: w(14) },
              { text: 'livrés', at: w(15), color: C.red },
              { text: '?', at: w(15) + 4, color: C.red },
            ]}
          />
        </AbsoluteFill>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: C.red, opacity: flash }} />
      <AbsoluteFill
        style={{
          background: C.brand,
          clipPath: `circle(${Math.pow(rush, 2.2) * 1250}px at 50% 50%)`,
        }}
      />
    </AbsoluteFill>
  )
}
