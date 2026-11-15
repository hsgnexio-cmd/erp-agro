import React from 'react'
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame } from 'remotion'
import { Carton, WIPE } from './components/Carton'
import { Sfx } from './components/Sfx'
import { Subtitles } from './components/Subtitles'
import { Cockpit, Dashboard } from './scenes/Act1'
import { Fefo, Mrp } from './scenes/Act2'
import { Forecast, Oee, Planning } from './scenes/Act3'
import { Recall, Trace } from './scenes/Act4'
import { End, Proof } from './scenes/Act5'
import { C } from './theme'
import { CARTON, CARTONS, FPS, MUSIC_OFFSET, SCENE_LIST, type SceneId, TOTAL, sec, voiceOf } from './timing'

const COMPONENTS: Record<SceneId, React.FC> = {
  a1a: Cockpit,
  a1b: Dashboard,
  a2a: Mrp,
  a2b: Fefo,
  a3a: Forecast,
  a3b: Planning,
  a3c: Oee,
  a4a: Trace,
  a4b: Recall,
  a5a: Proof,
  a5b: End,
}

// Fondu entre deux scènes d'un même acte (la fenêtre reste en place, l'écran change)
const FADE = 8
const afterCarton = (from: number) => CARTONS.some((carton) => carton.from + CARTON === from)

const Fade: React.FC<{ children: React.ReactNode; enabled: boolean }> = ({ children, enabled }) => {
  const frame = useCurrentFrame()
  const opacity = enabled ? interpolate(frame, [0, FADE], [0, 1], { extrapolateRight: 'clamp' }) : 1
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>
}

// Volumes : la voix devant, la musique très en retrait dessous (environ −26 dB), à peine
// relevée dans les silences
const VOICE_GAIN = 1.8
const MUSIC = { under: 0.05, free: 0.1 }

const speaking = (frame: number) =>
  SCENE_LIST.some((scene) => {
    const start = scene.from + sec(scene.voiceAt)
    return frame >= start - 4 && frame <= start + sec(voiceOf(scene.id).duration) + 4
  })

const musicVolume = (frame: number) => {
  // Moyenne glissante : la musique descend et remonte en douceur autour de la voix
  let sum = 0
  const span = 9
  for (let f = frame - span; f <= frame + span; f += 1) sum += speaking(f) ? MUSIC.under : MUSIC.free
  const fadeIn = Math.min(1, frame / 30)
  const fadeOut = Math.min(1, Math.max(0, (TOTAL - 6 - frame) / 75))
  return (sum / (2 * span + 1)) * fadeIn * fadeOut
}

export const Demo: React.FC = () => {
  const frame = useCurrentFrame()
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      {SCENE_LIST.map((scene) => {
        const Scene = COMPONENTS[scene.id]
        const last = scene.to === TOTAL
        return (
          <Sequence key={scene.id} from={scene.from} durationInFrames={scene.to - scene.from + (last ? 0 : FADE)} name={scene.id}>
            <Fade enabled={!afterCarton(scene.from)}>
              <Scene />
            </Fade>
            <Subtitles id={scene.id} />
          </Sequence>
        )
      })}
      {CARTONS.map((carton, index) => (
        <Sequence key={carton.number} from={carton.from - WIPE} durationInFrames={CARTON + 2 * WIPE} name={`carton ${carton.number}`}>
          <Carton number={carton.number} title={carton.title} subtitle={carton.subtitle} first={index === 0} />
          <Sfx at={WIPE} name="carton" />
        </Sequence>
      ))}
      <Sequence from={Math.max(0, Math.round(-MUSIC_OFFSET))} name="musique">
        <Audio
          src={staticFile('musique.mp3')}
          trimBefore={Math.max(0, Math.round(MUSIC_OFFSET))}
          volume={(f) => musicVolume(f + Math.max(0, Math.round(-MUSIC_OFFSET)))}
        />
      </Sequence>
      {SCENE_LIST.map((scene) => (
        <Sequence key={scene.id} from={scene.from + sec(scene.voiceAt)} name={`voix ${scene.id}`}>
          <Audio src={staticFile(`voix/${scene.id}.mp3`)} volume={VOICE_GAIN} />
        </Sequence>
      ))}
      <AbsoluteFill
        style={{
          background: C.forestDark,
          opacity: interpolate(frame, [TOTAL - 16, TOTAL - 2], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          pointerEvents: 'none',
        }}
      />
    </AbsoluteFill>
  )
}

