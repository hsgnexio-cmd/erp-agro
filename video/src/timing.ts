import voice from '../public/voix/durations.json'

export const FPS = 30
export const WIDTH = 1920
export const HEIGHT = 1080

// Musique : 128 battements par minute ; le « drop » est à 19,81 s du morceau et doit tomber
// à 7 s de la vidéo, quand l'ERP apparaît (mesuré avec scripts/bpm.mjs).
export const BPM = 128
export const BEAT = 60 / BPM
export const DROP = 7
export const MUSIC_DROP = 19.81
export const MUSIC_START = MUSIC_DROP - DROP

export const sec = (seconds: number) => Math.round(seconds * FPS)
/** Image de la vidéo où tombe le k-ième temps après le drop. */
export const beat = (k: number) => sec(DROP + k * BEAT)

export type SceneId =
  | 'accroche' | 'reponse' | 'tracabilite' | 'rappel' | 'modules' | 'pilotage' | 'preuves' | 'fin'

// Chaque scène commence sur un temps de la musique ; la voix démarre un peu après
export const SCENES: Record<SceneId, { from: number; to: number; voiceAt: number }> = {
  accroche: { from: 0, to: beat(0), voiceAt: 0.4 },
  reponse: { from: beat(0), to: beat(10), voiceAt: 0.2 },
  tracabilite: { from: beat(10), to: beat(28), voiceAt: 0.25 },
  rappel: { from: beat(28), to: beat(48), voiceAt: 0.2 },
  modules: { from: beat(48), to: beat(68), voiceAt: 0.1 },
  pilotage: { from: beat(68), to: beat(84), voiceAt: 0.25 },
  preuves: { from: beat(84), to: beat(104), voiceAt: 0.2 },
  fin: { from: beat(104), to: beat(104) + sec(7.6), voiceAt: 0.35 },
}
export const TOTAL = SCENES.fin.to

type VoiceLine = { id: string; duration: number; words: { t: number; w: string }[] }
const VOICE = voice as VoiceLine[]
export const voiceOf = (id: SceneId) => VOICE.find((line) => line.id === id)!

/** Image (locale à la scène) où la voix prononce le n-ième mot (à partir de 0). */
export const word = (id: SceneId, index: number) =>
  sec(SCENES[id].voiceAt + voiceOf(id).words[index].t)

/** Pulsation de 1 (sur le temps) à 0, à partir du drop. */
export const pulse = (globalFrame: number, sharpness = 5) => {
  const t = globalFrame / FPS - DROP
  if (t < 0) return 0
  const phase = (t / BEAT) % 1
  return Math.exp(-phase * sharpness)
}
