import { Easing, interpolate, spring } from 'remotion'

export const FPS = 30
const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

/** Apparition avec un léger ressort (0 → 1) à partir de l'image `at`. */
export const pop = (frame: number, at: number, stiffness = 170, damping = 18) =>
  spring({ frame: frame - at, fps: FPS, config: { damping, stiffness, mass: 0.7 } })

/** Apparition sans rebond. */
export const glide = (frame: number, at: number, duration = 14) =>
  interpolate(frame, [at, at + duration], [0, 1], { ...CLAMP, easing: Easing.out(Easing.cubic) })

/** 1 pendant [from, to], avec fondu d'entrée et de sortie. */
export const visible = (frame: number, from: number, to: number, fade = 8) =>
  interpolate(frame, [from, from + fade, to - fade, to], [0, 1, 1, 0], CLAMP)

/**
 * Piste d'animation : liste de repères { at, ...valeurs }. Entre deux repères, chaque valeur
 * glisse en douceur (départ et arrivée ralentis) ; avant le premier et après le dernier, elle
 * reste fixe.
 */
export function track<T extends { at: number }>(frame: number, keys: T[]): T {
  if (frame <= keys[0].at) return keys[0]
  const last = keys[keys.length - 1]
  if (frame >= last.at) return last
  const index = keys.findIndex((key) => key.at > frame)
  const from = keys[index - 1]
  const to = keys[index]
  const p = Easing.inOut(Easing.cubic)((frame - from.at) / (to.at - from.at))
  const result: Record<string, unknown> = { ...to }
  for (const name of Object.keys(to)) {
    const a = (from as Record<string, unknown>)[name]
    const b = (to as Record<string, unknown>)[name]
    if (typeof a === 'number' && typeof b === 'number') result[name] = a + (b - a) * p
  }
  result.at = frame
  return result as T
}
