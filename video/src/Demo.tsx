import React from 'react'
import { AbsoluteFill, Audio, Sequence, staticFile } from 'remotion'
import { Accroche } from './scenes/Accroche'
import { Fin } from './scenes/Fin'
import { Modules } from './scenes/Modules'
import { Pilotage } from './scenes/Pilotage'
import { Preuves } from './scenes/Preuves'
import { Rappel } from './scenes/Rappel'
import { Reponse } from './scenes/Reponse'
import { Tracabilite } from './scenes/Tracabilite'
import { C } from './theme'
import { DROP, FPS, MUSIC_START, SCENES, type SceneId, TOTAL, sec, voiceOf } from './timing'

const ORDER: [SceneId, React.FC][] = [
  ['accroche', Accroche],
  ['reponse', Reponse],
  ['tracabilite', Tracabilite],
  ['rappel', Rappel],
  ['modules', Modules],
  ['pilotage', Pilotage],
  ['preuves', Preuves],
  ['fin', Fin],
]

// Volumes mesurés : la voix est montée (×1,4) et la musique baissée dessous, puis relevée
// dans les silences entre deux phrases
const VOICE_GAIN = 1.4
const MUSIC = { introUnder: 0.3, introFree: 0.55, under: 0.15, free: 0.42, hit: 0.75 }

const speaking = (frame: number) =>
  ORDER.some(([id]) => {
    const start = SCENES[id].from + sec(SCENES[id].voiceAt)
    return frame >= start && frame <= start + sec(voiceOf(id).duration)
  })

const musicVolume = (frame: number) => {
  // Moyenne glissante : la musique descend et remonte en douceur autour de la voix
  let sum = 0
  const span = 6
  for (let f = frame - span; f <= frame + span; f += 1) {
    const intro = f < sec(DROP) - 2
    const talk = speaking(f)
    sum += intro ? (talk ? MUSIC.introUnder : MUSIC.introFree) : talk ? MUSIC.under : MUSIC.free
  }
  let volume = sum / (2 * span + 1)
  // Le drop claque avant que la voix ne reprenne
  const sinceDrop = frame - sec(DROP)
  if (sinceDrop >= -1 && sinceDrop < 6) volume = Math.max(volume, MUSIC.hit)
  const fadeIn = Math.min(1, frame / 12)
  const fadeOut = Math.min(1, Math.max(0, (TOTAL - 4 - frame) / 50))
  return volume * fadeIn * fadeOut
}

export const Demo: React.FC = () => (
  <AbsoluteFill style={{ background: C.night }}>
    {ORDER.map(([id, Scene]) => (
      <Sequence key={id} from={SCENES[id].from} durationInFrames={SCENES[id].to - SCENES[id].from} name={id}>
        <Scene />
      </Sequence>
    ))}
    <Audio src={staticFile('musique.mp3')} trimBefore={Math.round(MUSIC_START * FPS)} volume={musicVolume} />
    {ORDER.map(([id]) => (
      <Sequence key={id} from={SCENES[id].from + sec(SCENES[id].voiceAt)} name={`voix ${id}`}>
        <Audio src={staticFile(`voix/${id}.mp3`)} volume={VOICE_GAIN} />
      </Sequence>
    ))}
  </AbsoluteFill>
)
