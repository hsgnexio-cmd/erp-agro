import React from 'react'
import { AbsoluteFill, Img, interpolate, staticFile } from 'remotion'
import { track } from '../anim'
import { C, FONT } from '../theme'

// Repère de la page de l'ERP : 1440 × 900 (taille des captures)
export const PAGE_W = 1440
export const PAGE_H = 900
// Fenêtre du navigateur dans l'image de 1920 × 1080
const BW = 1500
const K = BW / PAGE_W
const BAR = 44
const BX = (1920 - BW) / 2
const BY = 22
const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

/** Point de l'image (1920 × 1080) où se trouve un point de la page (1440 × 900). */
export const toFrame = (x: number, y: number): [number, number] => [BX + x * K, BY + BAR + y * K]

export type Shot = { at: number; src: string }
/** Repère de caméra : zoom, et point de la page (visible à l'écran) amené au centre de l'image. */
export type CameraKey = { at: number; zoom: number; x?: number; y?: number }
export type ScrollKey = { at: number; y: number }
export type CursorKey = { at: number; x: number; y: number; click?: boolean }

const Pointer: React.FC<{ frame: number; keys: CursorKey[] }> = ({ frame, keys }) => {
  if (frame < keys[0].at - 6) return null
  const { x, y } = track(frame, keys)
  const clicks = keys.filter((key) => key.click)
  const recent = clicks.findLast((key) => frame >= key.at)
  const since = recent ? frame - recent.at : 99
  const ripple = interpolate(since, [0, 12], [0, 1], CLAMP)
  const press = interpolate(since, [0, 2, 7], [1, 0.82, 1], CLAMP)
  return (
    <>
      {recent && since < 12 ? (
        <div
          style={{
            position: 'absolute',
            left: recent.x - 30,
            top: recent.y - 30,
            width: 60,
            height: 60,
            borderRadius: '50%',
            border: `3px solid ${C.forest}`,
            background: 'rgba(22,74,44,0.12)',
            opacity: 1 - ripple,
            transform: `scale(${0.3 + ripple})`,
          }}
        />
      ) : null}
      <svg
        width="30"
        height="30"
        viewBox="0 0 24 24"
        style={{
          position: 'absolute',
          left: x - 5,
          top: y - 3,
          opacity: interpolate(frame, [keys[0].at - 6, keys[0].at], [0, 1], CLAMP),
          transform: `scale(${press})`,
          transformOrigin: '20% 12%',
          filter: 'drop-shadow(0 2px 3px rgba(0,0,0,0.35))',
        }}
      >
        <path d="M4 2 L4 19 L8.5 15 L11.5 22 L14.5 20.8 L11.6 14 L18 14 Z" fill="#111" stroke="#fff" strokeWidth="1.4" />
      </svg>
    </>
  )
}

/**
 * Scène type : la fenêtre du navigateur, flottante sur fond clair, filmée par une caméra qui
 * zoome sur un point de la page puis revient à la vue d'ensemble.
 */
export const Stage: React.FC<{
  frame: number
  /** Captures affichées tour à tour (fondu court entre deux). */
  shots: Shot[]
  title?: string
  camera?: CameraKey[]
  /** Défilement vertical de la page, en pixels de la page. */
  scroll?: ScrollKey[]
  /** Hauteur de la barre du haut et largeur du menu, qui restent fixes pendant le défilement. */
  stickyTop?: number
  stickyLeft?: number
  cursor?: CursorKey[]
  /** Calque posé sur la page, dans le repère 1440 × 900 (suit la caméra, pas le défilement). */
  children?: React.ReactNode
  /** Calque posé sur l'image entière, hors caméra (repère 1920 × 1080). */
  overlay?: React.ReactNode
}> = ({
  frame,
  shots,
  title = 'ERP Brévanne Traiteur',
  camera = [{ at: 0, zoom: 1 }],
  scroll,
  stickyTop = 57,
  stickyLeft = 0,
  cursor,
  children,
  overlay,
}) => {
  // Caméra : le point visé (dans l'image) vient au centre, sans jamais sortir de la fenêtre
  const keys = camera.map((key) => {
    const [fx, fy] = key.x === undefined || key.y === undefined ? [960, 540] : toFrame(key.x, key.y)
    return { at: key.at, zoom: key.zoom, fx, fy }
  })
  const { zoom, fx, fy } = track(frame, keys)
  const pad = 46
  const bound = (value: number, low: number, high: number) => (low > high ? (low + high) / 2 : Math.min(high, Math.max(low, value)))
  const tx = bound(960 - fx * zoom, 1920 - (BX + BW + pad) * zoom, -(BX - pad) * zoom)
  const ty = bound(540 - fy * zoom, 1080 - (BY + BAR + PAGE_H * K + pad) * zoom, -(BY - pad) * zoom)
  const scrollY = scroll ? track(frame, scroll).y : 0
  const index = Math.max(0, shots.findLastIndex((shot) => frame >= shot.at))
  const current = shots[index]
  const previous = index > 0 ? shots[index - 1] : null
  const fade = interpolate(frame, [current.at, current.at + 4], [0, 1], CLAMP)

  const page = (src: string, opacity = 1) => (
    <div style={{ position: 'absolute', inset: 0, opacity }}>
      <Img src={staticFile(src)} style={{ width: BW, display: 'block', transform: `translateY(${-scrollY * K}px)` }} />
      {scrollY > 0 && stickyLeft > 0 ? (
        <div style={{ position: 'absolute', left: 0, top: 0, width: stickyLeft * K, height: '100%', overflow: 'hidden' }}>
          <Img src={staticFile(src)} style={{ width: BW, maxWidth: 'none', display: 'block' }} />
        </div>
      ) : null}
      {scrollY > 0 && stickyTop > 0 ? (
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: '100%',
            height: stickyTop * K,
            overflow: 'hidden',
            boxShadow: '0 1px 0 rgba(0,0,0,0.06)',
          }}
        >
          <Img src={staticFile(src)} style={{ width: BW, maxWidth: 'none', display: 'block' }} />
        </div>
      ) : null}
    </div>
  )

  return (
    <AbsoluteFill style={{ background: C.paper, fontFamily: FONT }}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transformOrigin: '0 0',
          transform: `translate(${tx}px, ${ty}px) scale(${zoom})`,
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: BX,
            top: BY,
            width: BW,
            borderRadius: 16,
            overflow: 'hidden',
            background: C.white,
            boxShadow:
              '0 0 0 1px rgba(16,58,34,0.08), 0 12px 28px rgba(16,58,34,0.08), 0 40px 90px rgba(16,58,34,0.16)',
          }}
        >
          <div style={{ height: BAR, background: '#ECEFE8', display: 'flex', alignItems: 'center', padding: '0 18px', gap: 8 }}>
            {['#ff5f57', '#febc2e', '#28c840'].map((color) => (
              <div key={color} style={{ width: 12, height: 12, borderRadius: '50%', background: color }} />
            ))}
            <div
              style={{
                margin: '0 auto',
                width: 560,
                height: 26,
                borderRadius: 13,
                background: C.white,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 14,
                fontWeight: 500,
                color: C.muted,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
              }}
            >
              {title}
            </div>
            <div style={{ width: 52 }} />
          </div>
          <div style={{ width: BW, height: PAGE_H * K, overflow: 'hidden', position: 'relative', background: C.paper }}>
            {previous && fade < 1 ? page(previous.src) : null}
            {page(current.src, previous ? fade : 1)}
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                width: PAGE_W,
                height: PAGE_H,
                transformOrigin: '0 0',
                transform: `scale(${K})`,
              }}
            >
              {children}
              {cursor ? <Pointer frame={frame} keys={cursor} /> : null}
            </div>
          </div>
        </div>
      </div>
      {overlay}
    </AbsoluteFill>
  )
}

/** Cadre qui entoure une zone de la page (repère 1440 × 900) au moment où la voix en parle. */
export const Spot: React.FC<{
  frame: number
  from: number
  to: number
  rect: [number, number, number, number]
  color?: string
  pad?: number
}> = ({ frame, from, to, rect, color = C.forest, pad = 6 }) => {
  if (frame < from || frame > to) return null
  const enter = interpolate(frame, [from, from + 8], [0, 1], CLAMP)
  const leave = interpolate(frame, [to - 6, to], [1, 0], CLAMP)
  const [x, y, w, h] = rect
  return (
    <div
      style={{
        position: 'absolute',
        left: x - pad,
        top: y - pad,
        width: w + 2 * pad,
        height: h + 2 * pad,
        borderRadius: 12,
        border: `3px solid ${color}`,
        boxShadow: `0 0 0 6px ${color}22`,
        opacity: enter * leave,
        transform: `scale(${1.08 - 0.08 * enter})`,
      }}
    />
  )
}
