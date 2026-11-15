import React from 'react'
import { useCurrentFrame } from 'remotion'
import { Note } from '../components/Note'
import { Sfx } from '../components/Sfx'
import { Spot, Stage } from '../components/Stage'
import { C } from '../theme'
import { lengthOf, said } from '../timing'

/** Acte 3, première partie : la prévision de vente à 8 semaines, puis sa fiabilité. */
export const Forecast: React.FC = () => {
  const frame = useCurrentFrame()
  const s = (text: string) => said('a3a', text)
  const end = lengthOf('a3a')
  const weeks = s('huit')
  const promo = s('promotions')
  const actual = s('confrontée') - 4
  return (
    <Stage
      frame={frame}
      title="ERP Brévanne Traiteur · Prévisions de vente"
      shots={[
        { at: 0, src: 'captures/previsions.jpg' },
        { at: actual, src: 'captures/previsions-fiabilite.jpg' },
      ]}
      camera={[
        { at: 0, zoom: 1 },
        { at: weeks - 10, zoom: 1 },
        { at: weeks + 8, zoom: 1.5, x: 900, y: 470 },
        { at: promo - 6, zoom: 1.5, x: 900, y: 470 },
        { at: promo + 10, zoom: 1.75, x: 1080, y: 600 },
        { at: actual - 2, zoom: 1.75, x: 1080, y: 600 },
        { at: actual + 14, zoom: 1.5, x: 836, y: 470 },
        { at: end - 14, zoom: 1.5, x: 836, y: 470 },
        { at: end, zoom: 1 },
      ]}
      cursor={[
        { at: weeks - 4, x: 700, y: 520 },
        { at: weeks + 10, x: 900, y: 386 },
        { at: promo - 2, x: 900, y: 386 },
        { at: promo + 12, x: 1300, y: 612 },
        { at: actual + 2, x: 1300, y: 612 },
        { at: actual + 16, x: 1040, y: 575 },
      ]}
      overlay={
        <>
          <Note frame={frame} from={promo + 4} to={actual - 2} corner="top-left" label="Promotion enseigne" title="Volume × 1,8 sur deux semaines" />
          <Note
            frame={frame}
            from={actual + 8}
            to={end - 12}
            label="Fiabilité à S-1"
            title="90,6 % pour un objectif de 80 %"
            detail="Version figée chaque lundi, comparée aux commandes"
          />
        </>
      }
    >
      <Spot frame={frame} from={weeks + 4} to={promo - 2} rect={[620, 366, 780, 38]} pad={2} />
      <Spot frame={frame} from={promo + 6} to={actual - 2} rect={[1186, 584, 216, 42]} pad={2} color={C.amber} />
      <Spot frame={frame} from={actual + 12} to={end - 12} rect={[269, 500, 1135, 95]} pad={2} />
      <Sfx at={actual} name="glisse" />
    </Stage>
  )
}

/** Acte 3, deuxième partie : le plan de production figé à J-2, puis la charge des lignes. */
export const Planning: React.FC = () => {
  const frame = useCurrentFrame()
  const s = (text: string) => said('a3b', text)
  const end = lengthOf('a3b')
  const freeze = s('figé')
  const planning = s('planning') - 5
  const load = s('charge')
  const capacity = s('capacité')
  return (
    <Stage
      frame={frame}
      title={frame < planning ? 'ERP Brévanne Traiteur · Plan de production' : 'ERP Brévanne Traiteur · Planning'}
      shots={[
        { at: 0, src: 'captures/plan-production.jpg' },
        { at: planning, src: 'captures/planning.jpg' },
      ]}
      camera={[
        { at: 0, zoom: 1 },
        { at: 8, zoom: 1 },
        { at: freeze - 8, zoom: 1.4, x: 760, y: 560 },
        { at: freeze + 8, zoom: 1.7, x: 640, y: 430 },
        { at: planning - 4, zoom: 1.7, x: 640, y: 430 },
        { at: planning + 12, zoom: 1.2, x: 836, y: 450 },
        { at: load - 6, zoom: 1.2, x: 836, y: 450 },
        { at: load + 10, zoom: 2, x: 700, y: 540 },
        { at: capacity - 4, zoom: 2, x: 980, y: 540 },
        { at: end - 14, zoom: 2, x: 980, y: 540 },
        { at: end, zoom: 1 },
      ]}
      cursor={[
        { at: 6, x: 900, y: 640 },
        { at: freeze + 6, x: 448, y: 500 },
        { at: planning, x: 448, y: 500 },
        { at: load + 8, x: 540, y: 600 },
        { at: capacity + 4, x: 1060, y: 600 },
      ]}
      overlay={
        <>
          <Note
            frame={frame}
            from={freeze + 2}
            to={planning - 2}
            label="Plan figé à J-2"
            title="Samedi 12 h : les ordres de fabrication sont créés"
            detail="14 produits, 51 252 unités sur la semaine"
          />
          <Note
            frame={frame}
            from={load + 8}
            to={end - 12}
            label="Charge / capacité"
            title="15 h par jour et par ligne"
            detail="Orange à 85 %, rouge au-delà de 100 %"
          />
        </>
      }
    >
      <Spot frame={frame} from={freeze + 4} to={planning - 2} rect={[388, 477, 121, 40]} pad={4} />
      <Spot frame={frame} from={load + 6} to={end - 12} rect={[456, 578, 144, 30]} pad={3} />
      <Spot frame={frame} from={load + 12} to={end - 12} rect={[975, 578, 144, 30]} pad={3} />
      <Spot frame={frame} from={load + 18} to={end - 12} rect={[1147, 578, 144, 30]} pad={3} />
      <Sfx at={planning} name="glisse" />
    </Stage>
  )
}

// Cartes de la décomposition du TRS (trs.jpg)
const D: [number, number, number, number] = [268, 298, 256, 133]
const P: [number, number, number, number] = [561, 298, 256, 133]
const Q: [number, number, number, number] = [854, 298, 256, 133]
const T: [number, number, number, number] = [1147, 298, 256, 133]

/** Acte 3, troisième partie : TRS = disponibilité × performance × qualité. */
export const Oee: React.FC = () => {
  const frame = useCurrentFrame()
  const s = (text: string) => said('a3c', text)
  const end = lengthOf('a3c')
  const d = s('disponibilité')
  const p = s('performance')
  const q = s('qualité')
  const total = q + 16
  return (
    <Stage
      frame={frame}
      title="ERP Brévanne Traiteur · TRS des lignes"
      shots={[{ at: 0, src: 'captures/trs.jpg' }]}
      camera={[
        { at: 0, zoom: 1 },
        { at: s('TRS') - 8, zoom: 1 },
        { at: d, zoom: 1.55, x: 836, y: 400 },
        { at: total + 12, zoom: 1.55, x: 836, y: 400 },
        { at: end - 4, zoom: 1.3, x: 836, y: 520 },
        { at: end, zoom: 1.3, x: 836, y: 520 },
      ]}
      cursor={[
        { at: d - 8, x: 700, y: 560 },
        { at: d + 4, x: 400, y: 400 },
        { at: p + 4, x: 690, y: 400 },
        { at: q + 4, x: 985, y: 400 },
        { at: total + 6, x: 1280, y: 400 },
      ]}
      overlay={
        <Note
          frame={frame}
          from={total}
          to={end + 8}
          corner="top-left"
          label="TRS · objectif ≥ 70 %"
          title="85,9 % × 89,8 % × 98,9 % = 76,2 %"
          detail="7 lignes, arrêts classés par cause (Pareto)"
          mono
        />
      }
    >
      <Spot frame={frame} from={d} to={p - 2} rect={D} pad={3} />
      <Spot frame={frame} from={p} to={q - 2} rect={P} pad={3} />
      <Spot frame={frame} from={q} to={total - 2} rect={Q} pad={3} />
      <Spot frame={frame} from={total} to={end + 8} rect={T} pad={3} color={C.amber} />
      <Sfx at={d} name="touche" />
      <Sfx at={p} name="touche" />
      <Sfx at={q} name="touche" />
      <Sfx at={total} name="validation" />
    </Stage>
  )
}
