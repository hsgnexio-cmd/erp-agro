import { Easing, interpolate, spring } from 'remotion'
import { FPS } from './timing'

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

/** Apparition élastique (0 → 1) à partir de l'image `at`. */
export const pop = (frame: number, at: number, stiffness = 190, damping = 13) =>
  spring({ frame: frame - at, fps: FPS, config: { damping, stiffness, mass: 0.6 } })

/** Apparition sans rebond. */
export const glide = (frame: number, at: number, duration = 14) =>
  interpolate(frame, [at, at + duration], [0, 1], { ...CLAMP, easing: Easing.out(Easing.cubic) })

export const lerp = (frame: number, range: [number, number], out: [number, number], ease = true) =>
  interpolate(frame, range, out, {
    ...CLAMP,
    easing: ease ? Easing.inOut(Easing.cubic) : Easing.linear,
  })

/** 1 pendant [from, to], avec fondu d'entrée et de sortie. */
export const visible = (frame: number, from: number, to: number, fade = 6) =>
  interpolate(frame, [from, from + fade, to - fade, to], [0, 1, 1, 0], CLAMP)
