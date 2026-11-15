import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion'
import { glide, pop } from '../anim'
import { Sfx } from '../components/Sfx'
import { Stage } from '../components/Stage'
import { C, FONT, MONO } from '../theme'
import { lengthOf, said } from '../timing'

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

// La chaîne modélisée, dans l'ordre du flux
const FLOW = ['Prévisions', 'Plan de production', 'Besoins (MRP)', 'Réceptions et lots', 'Fabrication', 'Expéditions', 'Traçabilité']
const VIEWS = ['direction', 'acheteur', 'production', 'qualite']

const Stat: React.FC<{ frame: number; at: number; value: string; label: string }> = ({ frame, at, value, label }) => {
  const p = pop(frame, at)
  return (
    <div
      style={{
        width: 330,
        padding: '26px 30px 28px',
        borderRadius: 20,
        background: C.white,
        boxShadow: '0 2px 6px rgba(16,58,34,0.08), 0 22px 50px rgba(16,58,34,0.22)',
        opacity: glide(frame, at, 6),
        transform: `translateY(${(1 - p) * 30}px)`,
        fontFamily: FONT,
      }}
    >
      <div style={{ fontSize: 84, fontWeight: 800, lineHeight: 1, color: C.forest, fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      <div style={{ marginTop: 10, fontSize: 27, fontWeight: 500, color: C.muted, lineHeight: 1.25 }}>{label}</div>
    </div>
  )
}

/** Acte 5, première partie : la chaîne modélisée, les vues par métier, les tests. */
export const Proof: React.FC = () => {
  const frame = useCurrentFrame()
  const s = (text: string) => said('a5a', text)
  const end = lengthOf('a5a')
  const views = s('Chaque') - 6
  const tests = s('près') - 4
  // Première phrase : le schéma du flux ; deuxième : les vues par métier dans l'ERP
  const schema = interpolate(frame, [views - 6, views + 4], [1, 0], CLAMP)
  const each = Math.max(8, Math.round((tests - views) / VIEWS.length))
  const dim = interpolate(frame, [tests - 4, tests + 8], [0, 1], CLAMP)
  return (
    <AbsoluteFill style={{ background: C.paper, fontFamily: FONT }}>
      {frame >= views - 8 ? (
        <Stage
          frame={frame}
          title="ERP Brévanne Traiteur · Aperçu par métier"
          shots={VIEWS.map((role, index) => ({ at: views + index * each, src: `captures/vue-${role}.jpg` }))}
          camera={[
            { at: views, zoom: 1.35, x: 900, y: 300 },
            { at: tests - 2, zoom: 1.5, x: 980, y: 250 },
            { at: tests + 14, zoom: 1.12, x: 836, y: 450 },
            { at: end, zoom: 1.08, x: 836, y: 450 },
          ]}
          cursor={[
            { at: views + 2, x: 1100, y: 300 },
            { at: views + 10, x: 1270, y: 28 },
            ...VIEWS.slice(1).map((_, index) => ({ at: views + (index + 1) * each, x: 1270, y: 28, click: true })),
          ]}
        >
          {VIEWS.slice(1).map((role, index) => (
            <Sfx key={role} at={views + (index + 1) * each} name="clic" volume={0.8} />
          ))}
        </Stage>
      ) : null}
      {dim > 0 ? (
        <AbsoluteFill style={{ background: `rgba(246,247,244,${0.78 * dim})`, alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ display: 'flex', gap: 34 }}>
            <Stat frame={frame} at={tests} value="81" label="tables reliées, 12 règles métier côté serveur" />
            <Stat frame={frame} at={tests + 8} value="478" label="tests automatisés du serveur" />
            <Stat frame={frame} at={tests + 16} value="107" label="tests automatisés des écrans" />
          </div>
          <Sfx at={tests} name="validation" />
        </AbsoluteFill>
      ) : null}
      {schema > 0 ? (
        <AbsoluteFill style={{ background: C.paper, opacity: schema, alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
          <div style={{ fontSize: 30, fontWeight: 700, letterSpacing: '0.2em', color: C.forest, opacity: glide(frame, 2, 8) }}>
            MODÉLISER POUR COMPRENDRE
          </div>
          <div
            style={{
              marginTop: 26,
              fontSize: 78,
              fontWeight: 700,
              color: C.ink,
              textAlign: 'center',
              lineHeight: 1.1,
              opacity: glide(frame, 6, 10),
              transform: `translateY(${(1 - glide(frame, 6, 14)) * 22}px)`,
            }}
          >
            Toute la chaîne, de la prévision
            <br />
            à la livraison
          </div>
          <div style={{ marginTop: 70, width: 1700, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', alignItems: 'center', gap: '22px 0' }}>
            {FLOW.map((step, index) => {
              const at = s('rien') - 8 + index * 6
              const p = pop(frame, at)
              return (
                <React.Fragment key={step}>
                  {index > 0 ? (
                    <div style={{ width: 34 * glide(frame, at - 3, 5), height: 3, background: C.forest, opacity: 0.5 }} />
                  ) : null}
                  <div
                    style={{
                      padding: '14px 24px',
                      borderRadius: 14,
                      background: C.white,
                      border: `2px solid ${C.border}`,
                      boxShadow: '0 6px 18px rgba(16,58,34,0.08)',
                      fontSize: 30,
                      fontWeight: 600,
                      color: C.forest,
                      whiteSpace: 'nowrap',
                      opacity: glide(frame, at, 5),
                      transform: `scale(${0.85 + 0.15 * p})`,
                    }}
                  >
                    {step}
                  </div>
                </React.Fragment>
              )
            })}
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  )
}

const STACK = ['Django', 'React', 'PostgreSQL', 'Power BI']

/** Acte 5, seconde partie : écran de fin (titre, technologies, adresse du dépôt). */
export const End: React.FC = () => {
  const frame = useCurrentFrame()
  const s = (text: string) => said('a5b', text)
  const stack = s('bout') + 4
  const code = s('code') - 2
  const enter = interpolate(frame, [0, 9], [100, 0], CLAMP)
  return (
    <AbsoluteFill
      style={{
        background: C.forest,
        color: C.cream,
        fontFamily: FONT,
        clipPath: `inset(${enter}% 0 0 0)`,
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        textAlign: 'center',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 22, opacity: glide(frame, 8, 8) }}>
        <div
          style={{
            width: 74,
            height: 74,
            borderRadius: 18,
            background: C.accent,
            color: C.forestDark,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 28,
            fontWeight: 800,
          }}
        >
          ERP
        </div>
        <div style={{ fontSize: 44, fontWeight: 600 }}>Brévanne Traiteur</div>
      </div>
      <div
        style={{
          marginTop: 40,
          fontSize: 92,
          fontWeight: 700,
          lineHeight: 1.08,
          opacity: glide(frame, 12, 10),
          transform: `translateY(${(1 - glide(frame, 12, 14)) * 24}px)`,
        }}
      >
        Un ERP agroalimentaire,
        <br />
        modélisé de bout en bout
      </div>
      <div style={{ marginTop: 28, fontSize: 36, fontWeight: 500, color: 'rgba(247,240,220,0.8)', opacity: glide(frame, 20, 10) }}>
        Projet personnel de Nicolas Cloteaux · Supply chain du frais
      </div>
      <div style={{ marginTop: 60, display: 'flex', gap: 20 }}>
        {STACK.map((name, index) => {
          const at = stack + index * 7
          return (
            <div
              key={name}
              style={{
                padding: '14px 30px',
                borderRadius: 40,
                border: '2px solid rgba(247,240,220,0.45)',
                fontSize: 34,
                fontWeight: 600,
                whiteSpace: 'nowrap',
                opacity: glide(frame, at, 6),
                transform: `translateY(${(1 - pop(frame, at)) * 20}px)`,
              }}
            >
              {name}
            </div>
          )
        })}
      </div>
      <div
        style={{
          marginTop: 56,
          padding: '18px 40px',
          borderRadius: 18,
          background: C.cream,
          color: C.forestDark,
          fontFamily: MONO,
          fontSize: 42,
          fontWeight: 700,
          whiteSpace: 'nowrap',
          opacity: glide(frame, code, 8),
          transform: `scale(${0.94 + 0.06 * pop(frame, code)})`,
        }}
      >
        github.com/hsgnexio-cmd/erp-agro
      </div>
      {STACK.map((name, index) => (
        <Sfx key={name} at={stack + index * 7} name="touche" />
      ))}
      <Sfx at={code} name="validation" />
    </AbsoluteFill>
  )
}

