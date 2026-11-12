import React from 'react'
import { interpolate } from 'remotion'
import { glide, pop } from '../anim'
import { C, FONT, MONO } from '../theme'

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

/** Texte qui « claque » : arrive trop grand puis se pose. */
export const Slam: React.FC<{
  frame: number
  at: number
  children: React.ReactNode
  style?: React.CSSProperties
  from?: number
}> = ({ frame, at, children, style, from = 2.4 }) => {
  const p = pop(frame, at, 260, 16)
  const opacity = interpolate(frame, [at, at + 3], [0, 1], CLAMP)
  return (
    <div
      style={{
        display: 'inline-block',
        opacity,
        transform: `scale(${from + (1 - from) * p})`,
        ...style,
      }}
    >
      {children}
    </div>
  )
}

/** Texte qui monte en fondu. */
export const Rise: React.FC<{
  frame: number
  at: number
  children: React.ReactNode
  style?: React.CSSProperties
  distance?: number
  inline?: boolean
}> = ({ frame, at, children, style, distance = 46, inline }) => {
  const p = pop(frame, at, 170, 16)
  return (
    <div
      style={{
        display: inline ? 'inline-block' : 'block',
        opacity: glide(frame, at, 8),
        transform: `translateY(${(1 - p) * distance}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  )
}

/** Mots qui apparaissent un par un, chacun à son image (calés sur la voix). */
export const Words: React.FC<{
  frame: number
  words: { text: string; at: number; color?: string }[]
  style?: React.CSSProperties
}> = ({ frame, words, style }) => (
  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0 0.26em', ...style }}>
    {words.map((item, index) => (
      <Rise key={index} frame={frame} at={item.at} inline distance={38} style={{ color: item.color }}>
        {item.text}
      </Rise>
    ))}
  </div>
)

/** Nombre qui défile de 0 à sa valeur. */
export const Counter: React.FC<{
  frame: number
  at: number
  value: number
  duration?: number
  suffix?: string
}> = ({ frame, at, value, duration = 14, suffix = '' }) => {
  const p = interpolate(frame, [at, at + duration], [0, 1], CLAMP)
  const eased = 1 - Math.pow(1 - p, 3)
  return (
    <span style={{ fontVariantNumeric: 'tabular-nums' }}>
      {Math.round(value * eased)}
      {suffix}
    </span>
  )
}

export const Pill: React.FC<{
  children: React.ReactNode
  color?: string
  background?: string
  mono?: boolean
  size?: number
  style?: React.CSSProperties
}> = ({ children, color = C.night, background = C.lime, mono, size = 30, style }) => (
  <div
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: size * 0.4,
      padding: `${size * 0.36}px ${size * 0.8}px`,
      borderRadius: size * 2,
      background,
      color,
      fontFamily: mono ? MONO : FONT,
      fontWeight: mono ? 700 : 800,
      fontSize: size,
      letterSpacing: mono ? 0 : '0.02em',
      whiteSpace: 'nowrap',
      ...style,
    }}
  >
    {children}
  </div>
)
