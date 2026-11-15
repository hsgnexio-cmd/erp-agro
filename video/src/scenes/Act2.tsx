import React from 'react'
import { useCurrentFrame } from 'remotion'
import { Note } from '../components/Note'
import { Sfx } from '../components/Sfx'
import { Spot, Stage } from '../components/Stage'
import { C } from '../theme'
import { lengthOf, said } from '../timing'

/** Acte 2, première partie : le calcul des besoins nets (MRP) sur la crème fraîche. */
export const Mrp: React.FC = () => {
  const frame = useCurrentFrame()
  const s = (text: string, n = 1) => said('a2a', text, n)
  const end = lengthOf('a2a')
  const click = s('Stock') - 12
  const SCROLL = 150 // la page descend pour montrer tout le détail de l'article
  const stock = s('Stock')
  const receipts = s('réceptions')
  const gross = s('besoins', 2)
  const lead = s('Délais')
  const order = s('propose')
  const date = s('date')
  return (
    <Stage
      frame={frame}
      title="ERP Brévanne Traiteur · Besoins d'achat"
      shots={[
        { at: 0, src: 'captures/mrp.jpg' },
        { at: click + 2, src: 'captures/mrp-detail.jpg' },
      ]}
      scroll={[
        { at: click + 2, y: 0 },
        { at: click + 16, y: SCROLL },
      ]}
      stickyLeft={232}
      camera={[
        { at: 0, zoom: 1 },
        { at: 14, zoom: 1 },
        { at: click - 6, zoom: 1.3, x: 780, y: 560 },
        { at: click + 4, zoom: 1.3, x: 780, y: 560 },
        { at: stock + 6, zoom: 1.6, x: 800, y: 660 },
        { at: lead - 12, zoom: 1.6, x: 800, y: 660 },
        { at: lead + 8, zoom: 1.75, x: 760, y: 515 },
        { at: end - 16, zoom: 1.75, x: 860, y: 515 },
        { at: end, zoom: 1 },
      ]}
      cursor={[
        { at: 10, x: 760, y: 470 },
        { at: click - 2, x: 400, y: 666 },
        { at: click, x: 400, y: 666, click: true },
        { at: click + 16, x: 400, y: 666 - SCROLL },
        { at: stock + 10, x: 520, y: 760 },
        { at: lead - 6, x: 520, y: 760 },
        { at: lead + 10, x: 560, y: 520 },
        { at: date - 8, x: 560, y: 520 },
        { at: date + 6, x: 830, y: 524 },
      ]}
      overlay={
        <>
          <Note
            frame={frame}
            from={gross + 16}
            to={lead - 6}
            label="Net à commander · semaine 47"
            title="2 213,6 − 609,4 − 0 = 1 604,2 kg"
            detail="Besoin brut − stock disponible − à recevoir"
            mono
          />
          <Note
            frame={frame}
            from={lead + 6}
            to={end - 14}
            label="Crèmerie Bretonne · délai 3 jours"
            title="Besoin du 16/11 : à commander le 10/11"
            detail="Jours ouvrés du calendrier industriel"
            tone="red"
          />
        </>
      }
    >
      <Spot frame={frame} from={stock} to={receipts - 2} rect={[655, 702 - SCROLL, 520, 30]} />
      <Spot frame={frame} from={receipts} to={gross - 2} rect={[283, 811 - SCROLL, 1100, 44]} pad={2} />
      <Spot frame={frame} from={gross} to={gross + 26} rect={[283, 767 - SCROLL, 1100, 44]} pad={2} />
      <Spot frame={frame} from={gross + 16} to={lead - 8} rect={[283, 856 - SCROLL, 1100, 44]} pad={2} color={C.amber} />
      <Spot frame={frame} from={lead + 6} to={order} rect={[500, 650 - SCROLL, 105, 32]} />
      <Spot frame={frame} from={order} to={date - 2} rect={[1055, 650 - SCROLL, 145, 32]} />
      <Spot frame={frame} from={date} to={end - 14} rect={[748, 648 - SCROLL, 182, 36]} color={C.red} />
      <Sfx at={click} name="clic" />
      <Sfx at={click + 2} name="glisse" volume={0.6} />
      <Sfx at={gross + 16} name="validation" />
    </Stage>
  )
}

/** Acte 2, seconde partie : proposition FEFO, puis suivi des chambres froides. */
export const Fefo: React.FC = () => {
  const frame = useCurrentFrame()
  const s = (text: string, n = 1) => said('a2b', text, n)
  const end = lengthOf('a2b')
  const click = s('FEFO') - 4
  const first = s('premier')
  const gauges = s('jauges')
  const orderAt = s("l'ordre")
  const cold = s('chaque') - 6
  return (
    <Stage
      frame={frame}
      title={frame < cold ? 'ERP Brévanne Traiteur · FEFO' : 'ERP Brévanne Traiteur · Températures'}
      shots={[
        { at: 0, src: 'captures/fefo-saisie.jpg' },
        { at: click + 3, src: 'captures/fefo.jpg' },
        { at: cold, src: 'captures/temperatures.jpg' },
      ]}
      camera={[
        { at: 0, zoom: 1 },
        { at: click - 10, zoom: 1.2, x: 900, y: 330 },
        { at: click + 6, zoom: 1.2, x: 900, y: 330 },
        { at: first, zoom: 1.6, x: 836, y: 560 },
        { at: gauges - 8, zoom: 1.6, x: 836, y: 560 },
        { at: gauges + 8, zoom: 2.1, x: 900, y: 598 },
        { at: orderAt + 6, zoom: 2.1, x: 900, y: 598 },
        { at: orderAt + 24, zoom: 1.6, x: 836, y: 580 },
        { at: cold - 4, zoom: 1.6, x: 836, y: 580 },
        { at: cold + 12, zoom: 1.15, x: 836, y: 470 },
        { at: s('suivie') - 4, zoom: 1.15, x: 836, y: 470 },
        { at: s('suivie') + 14, zoom: 1.9, x: 700, y: 492 },
        { at: end - 16, zoom: 1.9, x: 700, y: 492 },
        { at: end, zoom: 1 },
      ]}
      cursor={[
        { at: 4, x: 1100, y: 420 },
        { at: click - 2, x: 1307, y: 317 },
        { at: click, x: 1307, y: 317, click: true },
        { at: first + 4, x: 1100, y: 640 },
        { at: gauges, x: 1100, y: 640 },
        { at: gauges + 12, x: 960, y: 590 },
        { at: orderAt, x: 960, y: 590 },
        { at: orderAt + 16, x: 1360, y: 600 },
        { at: cold + 4, x: 1100, y: 620 },
        { at: s('suivie') + 14, x: 740, y: 520 },
      ]}
      overlay={
        <>
          <Note
            frame={frame}
            from={first + 6}
            to={gauges - 4}
            label="First Expired, First Out"
            title="Lot du 24/11 avant celui du 02/12"
            detail="Seuls les lots libérés sont proposés"
          />
          <Note
            frame={frame}
            from={s('suivie') + 10}
            to={end - 14}
            label="Chaîne du froid"
            title="7,8 °C relevé pour une limite de 4 °C"
            detail="Alerte et blocage automatique des lots présents"
            tone="red"
          />
        </>
      }
    >
      <Spot frame={frame} from={first} to={gauges - 2} rect={[269, 553, 1134, 45]} pad={2} />
      <Spot frame={frame} from={gauges} to={orderAt - 2} rect={[735, 556, 345, 86]} pad={2} />
      <Spot frame={frame} from={orderAt + 12} to={cold - 2} rect={[1285, 556, 118, 86]} pad={2} />
      <Spot frame={frame} from={s('suivie') + 8} to={end - 14} rect={[556, 400, 274, 186]} pad={3} color={C.red} />
      <Sfx at={click} name="clic" />
      <Sfx at={click + 3} name="validation" />
      <Sfx at={cold} name="glisse" />
    </Stage>
  )
}
