import React from 'react'
import { useCurrentFrame } from 'remotion'
import { Note } from '../components/Note'
import { Sfx } from '../components/Sfx'
import { Spot, Stage } from '../components/Stage'
import { C } from '../theme'
import { lengthOf, said } from '../timing'

const TYPED = 14 // caractères de « LR-261113-0005 » (images palette-00 à palette-14)
const pad = (n: number) => String(n).padStart(2, '0')

/** Acte 4, première partie : recherche du lot de crème, tiroir, arbre de traçabilité. */
export const Trace: React.FC = () => {
  const frame = useCurrentFrame()
  const s = (text: string) => said('a4a', text)
  const end = lengthOf('a4a')
  const open = 10
  const typeFrom = s('un') - 2
  const typeTo = s('Une') - 8
  const enter = s('recherche')
  const tab = s('traçabilité') - 8
  const made = s('fabrications')
  const finished = s('produits')
  const shipped = s('expéditions')
  const recall = end - 5
  // Une image par caractère tapé : la liste des résultats se resserre à chaque frappe
  const typing = Array.from({ length: TYPED }, (_, i) => ({
    at: Math.round(typeFrom + ((i + 1) * (typeTo - typeFrom)) / TYPED),
    src: `captures/palette-${pad(i + 1)}.jpg`,
  }))
  return (
    <Stage
      frame={frame}
      title="ERP Brévanne Traiteur · Lots"
      shots={[
        { at: 0, src: 'captures/lots.jpg' },
        { at: open, src: 'captures/palette-00.jpg' },
        ...typing,
        { at: enter + 3, src: 'captures/tiroir-detail.jpg' },
        { at: tab + 2, src: 'captures/tiroir-trace.jpg' },
      ]}
      camera={[
        { at: 0, zoom: 1 },
        { at: open - 2, zoom: 1 },
        { at: open + 14, zoom: 1.75, x: 720, y: 210 },
        { at: enter, zoom: 1.75, x: 720, y: 210 },
        { at: enter + 14, zoom: 1.2, x: 1000, y: 400 },
        { at: tab, zoom: 1.2, x: 1000, y: 400 },
        { at: made - 6, zoom: 1.7, x: 1110, y: 520 },
        { at: recall - 22, zoom: 1.7, x: 1110, y: 540 },
        { at: recall - 6, zoom: 1.7, x: 1180, y: 700 },
        { at: end, zoom: 1.7, x: 1180, y: 700 },
      ]}
      cursor={[
        { at: 2, x: 980, y: 420 },
        { at: open, x: 1010, y: 30, click: true },
        { at: enter - 14, x: 1010, y: 30 },
        { at: enter - 2, x: 760, y: 205 },
        { at: enter, x: 760, y: 205, click: true },
        { at: tab - 10, x: 1020, y: 260 },
        { at: tab, x: 899, y: 107, click: true },
        { at: made, x: 1300, y: 420 },
        { at: shipped, x: 1320, y: 560 },
        { at: recall - 18, x: 1320, y: 560 },
        { at: recall, x: 1305, y: 866, click: true },
      ]}
      overlay={
        <>
          <Note
            frame={frame}
            from={open + 6}
            to={enter - 2}
            corner="top-left"
            label="Recherche globale · Ctrl K"
            title="Lot, article, enseigne, fournisseur, OF"
          />
          <Note
            frame={frame}
            from={made - 4}
            to={end + 8}
            corner="top-left"
            label="Traçabilité aval"
            title="Matière → fabrications → produits finis → clients"
            detail="Chaque consommation et chaque livraison, avec les quantités"
          />
        </>
      }
    >
      <Spot frame={frame} from={made} to={finished - 2} rect={[812, 628, 608, 92]} pad={3} />
      <Spot frame={frame} from={finished} to={shipped - 2} rect={[812, 372, 608, 92]} pad={3} color={C.red} />
      <Spot frame={frame} from={shipped} to={recall - 16} rect={[812, 472, 608, 148]} pad={3} />
      <Sfx at={open} name="clic" />
      {Array.from({ length: TYPED }, (_, i) => (
        <Sfx key={i} at={typing[i].at} name="touche" volume={i % 2 === 0 ? 1 : 0.8} />
      ))}
      <Sfx at={enter} name="clic" />
      <Sfx at={enter + 3} name="glisse" />
      <Sfx at={tab} name="clic" />
      <Sfx at={recall} name="clic" />
    </Stage>
  )
}

/** Acte 4, seconde partie : le rappel lancé, les stocks bloqués, les enseignes à prévenir. */
export const Recall: React.FC = () => {
  const frame = useCurrentFrame()
  const s = (text: string) => said('a4b', text)
  const end = lengthOf('a4b')
  const launched = s('lancé') - 6
  const lots = s('Quatorze')
  const stock = s('stock')
  const blocked = s('bloqué')
  const customers = s('six')
  const exact = s('quantités')
  return (
    <Stage
      frame={frame}
      title="ERP Brévanne Traiteur · Rappel RAP-2026-00001"
      shots={[
        { at: 0, src: 'captures/simulation.jpg' },
        { at: launched, src: 'captures/rappel.jpg' },
      ]}
      stickyLeft={232}
      scroll={[
        { at: 0, y: 0 },
        { at: blocked - 10, y: 0 },
        { at: blocked + 8, y: 250 },
        { at: customers - 12, y: 250 },
        { at: customers + 10, y: 1440 },
        { at: end - 14, y: 1500 },
      ]}
      camera={[
        { at: 0, zoom: 1.2, x: 800, y: 330 },
        { at: launched, zoom: 1.2, x: 800, y: 330 },
        { at: lots - 2, zoom: 1.55, x: 760, y: 300 },
        { at: stock - 4, zoom: 1.55, x: 760, y: 300 },
        { at: stock + 10, zoom: 1.55, x: 900, y: 300 },
        { at: blocked - 8, zoom: 1.55, x: 900, y: 300 },
        { at: blocked + 10, zoom: 1.75, x: 1030, y: 420 },
        { at: customers - 10, zoom: 1.75, x: 1030, y: 420 },
        { at: customers + 12, zoom: 1.3, x: 780, y: 450 },
        { at: end - 14, zoom: 1.3, x: 780, y: 450 },
        { at: end, zoom: 1.2, x: 780, y: 450 },
      ]}
      cursor={[
        { at: lots - 6, x: 700, y: 520 },
        { at: lots + 6, x: 470, y: 345 },
        { at: stock + 8, x: 840, y: 345 },
        { at: blocked + 12, x: 1090, y: 345 },
        { at: customers - 8, x: 1090, y: 345 },
        { at: customers + 14, x: 420, y: 330 },
        { at: exact + 10, x: 420, y: 520 },
      ]}
      overlay={
        <>
          <Note
            frame={frame}
            from={launched + 2}
            to={blocked - 6}
            label="Rappel RAP-2026-00001"
            title="Crème fraîche · lot LR-261113-0005"
            detail="Contamination signalée par le fournisseur"
            tone="red"
          />
          <Note
            frame={frame}
            from={blocked + 4}
            to={customers - 6}
            corner="top-left"
            label="Blocage immédiat"
            title="6 lots avec du stock, bloqués par ce rappel"
            tone="red"
          />
          <Note
            frame={frame}
            from={customers + 8}
            to={end + 8}
            label="Clients à prévenir"
            title="6 enseignes, entrepôt par entrepôt"
            detail="Liste exportable vers Excel, quantités livrées par lot"
          />
        </>
      }
    >
      <Spot frame={frame} from={lots} to={stock - 2} rect={[268, 282, 367, 107]} pad={3} />
      <Spot frame={frame} from={stock} to={blocked - 8} rect={[652, 282, 367, 107]} pad={3} color={C.red} />
      <Spot frame={frame} from={blocked + 10} to={customers - 10} rect={[1008, 316, 168, 30]} pad={3} color={C.red} />
      <Spot frame={frame} from={customers + 14} to={end + 8} rect={[272, 170, 190, 640]} pad={2} />
      <Sfx at={launched} name="alerte" />
      <Sfx at={lots} name="touche" />
      <Sfx at={stock} name="touche" />
      <Sfx at={customers + 10} name="glisse" volume={0.6} />
    </Stage>
  )
}
