import React from 'react'
import { useCurrentFrame } from 'remotion'
import { Note } from '../components/Note'
import { Sfx } from '../components/Sfx'
import { Spot, Stage } from '../components/Stage'
import { C } from '../theme'
import { lengthOf, said } from '../timing'

/** Acte 1, première partie : le cockpit d'accueil et ses urgences du jour. */
export const Cockpit: React.FC = () => {
  const frame = useCurrentFrame()
  const s = (text: string, n = 1) => said('a1a', text, n)
  const end = lengthOf('a1a')
  const perishable = s('matières')
  const dlc = s('DLC')
  const zero = s('zéro')
  return (
    <Stage
      frame={frame}
      title="ERP Brévanne Traiteur · Accueil"
      shots={[{ at: 0, src: 'captures/accueil.jpg' }]}
      camera={[
        { at: 0, zoom: 1.04 },
        { at: s('tension') - 12, zoom: 1.04 },
        { at: perishable - 4, zoom: 1.5, x: 836, y: 305 },
        { at: dlc - 12, zoom: 1.5, x: 836, y: 305 },
        { at: dlc + 10, zoom: 1.7, x: 980, y: 700 },
        { at: zero - 12, zoom: 1.7, x: 980, y: 700 },
        { at: zero + 10, zoom: 1.5, x: 836, y: 300 },
        { at: end - 16, zoom: 1.5, x: 836, y: 300 },
        { at: end, zoom: 1 },
      ]}
      cursor={[
        { at: perishable - 10, x: 700, y: 520 },
        { at: perishable + 6, x: 1336, y: 306 },
        { at: dlc - 6, x: 1336, y: 306 },
        { at: dlc + 12, x: 1010, y: 742 },
        { at: zero - 6, x: 1010, y: 742 },
        { at: zero + 14, x: 370, y: 428 },
      ]}
      overlay={
        <>
          <Note frame={frame} from={perishable} to={dlc - 4} label="Périssable" title="DLC dépassée : lot bloqué automatiquement" />
          <Note frame={frame} from={dlc + 4} to={zero - 4} corner="top-left" label="Contrat enseigne" title="DLC minimale à la livraison" detail="Un lot trop court est bloqué pour ce client" />
          <Note frame={frame} from={zero + 4} to={end - 14} label="Chaîne du froid" title="Écart de température : expédition refusée" tone="red" />
        </>
      }
    >
      <Spot frame={frame} from={perishable} to={dlc - 6} rect={[280, 280, 1112, 50]} color={C.amber} />
      <Spot frame={frame} from={dlc + 10} to={zero - 8} rect={[843, 664, 273, 119]} />
      <Spot frame={frame} from={zero + 8} to={end - 14} rect={[280, 217, 1112, 50]} color={C.red} />
      <Spot frame={frame} from={zero + 14} to={end - 14} rect={[280, 343, 1112, 50]} color={C.red} />
      <Sfx at={perishable} name="glisse" volume={0.5} />
      <Sfx at={zero + 8} name="alerte" volume={0.6} />
    </Stage>
  )
}

// Cartes du tableau de bord (captures/rects.json, dashboard.jpg)
const KPI = {
  service: [268, 343, 272, 236],
  demarque: [556, 343, 272, 236],
  coverPf: [844, 343, 272, 236],
  coverMp: [1132, 343, 272, 236],
  forecast: [844, 594, 272, 236],
} satisfies Record<string, [number, number, number, number]>

/** Acte 1, seconde partie : les indicateurs qui arbitrent entre coût, service et fraîcheur. */
export const Dashboard: React.FC = () => {
  const frame = useCurrentFrame()
  const s = (text: string) => said('a1b', text)
  const end = lengthOf('a1b')
  const service = s('taux')
  const shrink = s('démarque')
  const cover = s('couverture')
  const forecast = s('fiabilité')
  return (
    <Stage
      frame={frame}
      title="ERP Brévanne Traiteur · Tableau de bord"
      shots={[{ at: 0, src: 'captures/dashboard.jpg' }]}
      camera={[
        { at: 0, zoom: 1 },
        { at: service - 14, zoom: 1 },
        { at: service + 4, zoom: 1.62, x: 600, y: 470 },
        { at: cover - 10, zoom: 1.62, x: 640, y: 470 },
        { at: cover + 8, zoom: 1.62, x: 1070, y: 470 },
        { at: forecast - 8, zoom: 1.62, x: 1070, y: 470 },
        { at: forecast + 10, zoom: 1.62, x: 1000, y: 690 },
        { at: end - 14, zoom: 1.62, x: 1000, y: 690 },
        { at: end, zoom: 1 },
      ]}
      cursor={[
        { at: service - 8, x: 760, y: 640 },
        { at: service + 6, x: 430, y: 440 },
        { at: shrink - 4, x: 430, y: 440 },
        { at: shrink + 8, x: 700, y: 430 },
        { at: cover - 2, x: 700, y: 430 },
        { at: cover + 12, x: 1120, y: 470 },
        { at: forecast - 2, x: 1120, y: 470 },
        { at: forecast + 12, x: 990, y: 720 },
      ]}
    >
      <Spot frame={frame} from={service} to={shrink - 2} rect={KPI.service} color={C.red} pad={3} />
      <Spot frame={frame} from={shrink} to={cover - 2} rect={KPI.demarque} pad={3} />
      <Spot frame={frame} from={cover} to={forecast - 2} rect={KPI.coverPf} color={C.red} pad={3} />
      <Spot frame={frame} from={cover + 5} to={forecast - 2} rect={KPI.coverMp} pad={3} />
      <Spot frame={frame} from={forecast} to={end - 12} rect={KPI.forecast} pad={3} />
      <Sfx at={service} name="touche" />
      <Sfx at={shrink} name="touche" />
      <Sfx at={cover} name="touche" />
      <Sfx at={forecast} name="touche" />
    </Stage>
  )
}
