import voice from '../public/voix/durations.json'
import { FPS } from './anim'

export { FPS }
export const WIDTH = 1920
export const HEIGHT = 1080

export const sec = (seconds: number) => Math.round(seconds * FPS)

export type SceneId =
  | 'a1a' | 'a1b' | 'a2a' | 'a2b' | 'a3a' | 'a3b' | 'a3c' | 'a4a' | 'a4b' | 'a5a' | 'a5b'

type VoiceLine = { id: string; duration: number; words: { t: number; w: string }[] }
const VOICE = voice as VoiceLine[]
export const voiceOf = (id: SceneId) => VOICE.find((line) => line.id === id)!

/** Cartons de titre : un par acte, placé avant la scène indiquée. */
export const ACTS: { before: SceneId; number: number; title: string; subtitle: string }[] = [
  { before: 'a1a', number: 1, title: "L'équation du frais", subtitle: 'Coût · Service · Fraîcheur' },
  { before: 'a2a', number: 2, title: 'Approvisionner', subtitle: 'Ni rupture, ni perte' },
  { before: 'a3a', number: 3, title: "De la prévision à l'atelier", subtitle: 'Prévoir · Planifier · Mesurer' },
  { before: 'a4a', number: 4, title: 'Le crash-test', subtitle: "Rappel d'un lot contaminé" },
  { before: 'a5a', number: 5, title: 'La preuve', subtitle: 'Modéliser pour comprendre' },
]
export const CARTON = sec(1.1)

// Temps laissé avant la voix (lead) et après (tail), en secondes, pour chaque scène
const ORDER: { id: SceneId; lead: number; tail: number }[] = [
  { id: 'a1a', lead: 0.35, tail: 0.3 },
  { id: 'a1b', lead: 0.3, tail: 0.6 },
  { id: 'a2a', lead: 0.35, tail: 0.4 },
  { id: 'a2b', lead: 0.4, tail: 0.6 },
  { id: 'a3a', lead: 0.35, tail: 0.4 },
  { id: 'a3b', lead: 0.35, tail: 0.4 },
  { id: 'a3c', lead: 0.35, tail: 0.7 },
  { id: 'a4a', lead: 0.35, tail: 0.4 },
  { id: 'a4b', lead: 0.4, tail: 0.8 },
  { id: 'a5a', lead: 0.35, tail: 0.4 },
  { id: 'a5b', lead: 0.5, tail: 4.2 },
]

export type Scene = { id: SceneId; from: number; to: number; voiceAt: number }
export const SCENE_LIST: Scene[] = []
export const CARTONS: { from: number; number: number; title: string; subtitle: string }[] = []
{
  let cursor = 0
  for (const item of ORDER) {
    const act = ACTS.find((entry) => entry.before === item.id)
    if (act) {
      CARTONS.push({ from: cursor, number: act.number, title: act.title, subtitle: act.subtitle })
      cursor += CARTON
    }
    const length = sec(item.lead + voiceOf(item.id).duration + item.tail)
    SCENE_LIST.push({ id: item.id, from: cursor, to: cursor + length, voiceAt: item.lead })
    cursor += length
  }
}
export const SCENES = Object.fromEntries(SCENE_LIST.map((scene) => [scene.id, scene])) as Record<SceneId, Scene>
export const TOTAL = SCENE_LIST[SCENE_LIST.length - 1].to

/** Durée d'une scène, en images. */
export const lengthOf = (id: SceneId) => SCENES[id].to - SCENES[id].from

/** Image (locale à la scène) où la voix prononce le n-ième mot (à partir de 0). */
export const word = (id: SceneId, index: number) => {
  const words = voiceOf(id).words
  return sec(SCENES[id].voiceAt + words[Math.min(index, words.length - 1)].t)
}

/** Image (locale à la scène) où la voix prononce pour la première fois le mot donné. */
export const said = (id: SceneId, text: string, occurrence = 1) => {
  const words = voiceOf(id).words
  let seen = 0
  const index = words.findIndex((item) => {
    if (!item.w.toLowerCase().startsWith(text.toLowerCase())) return false
    seen += 1
    return seen === occurrence
  })
  if (index < 0) throw new Error(`Mot « ${text} » absent de la voix ${id}`)
  return word(id, index)
}

// Musique : le temps fort du morceau (à 19,81 s) tombe sur le carton de l'acte 2
export const MUSIC_DROP = 19.81
export const MUSIC_OFFSET = MUSIC_DROP * FPS - CARTONS[1].from
