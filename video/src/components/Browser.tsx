import React from 'react'
import { Img, staticFile } from 'remotion'
import { FONT } from '../theme'

export const PAGE_WIDTH = 1440
export const PAGE_HEIGHT = 900

/** Fenêtre de navigateur contenant une capture de l'ERP (défilement et zoom animables). */
export const Browser: React.FC<{
  src: string
  width: number
  title?: string
  /** Défilement vertical, en pixels de la page (largeur de référence : 1440). */
  scroll?: number
  zoom?: number
  /** Largeur (px de la page) du menu latéral, qui reste fixe pendant le défilement. */
  sticky?: number
  /** Point fixe du zoom, de 0 à 1. */
  focus?: [number, number]
  /** Calque posé sur la page, dans le repère 1440 × 900. */
  children?: React.ReactNode
  style?: React.CSSProperties
}> = ({
  src,
  width,
  title = 'ERP Brévanne Traiteur',
  scroll = 0,
  sticky = 0,
  zoom = 1,
  focus = [0.5, 0.5],
  children,
  style,
}) => {
  const k = width / PAGE_WIDTH
  const bar = Math.round(46 * Math.max(k, 0.6))
  return (
    <div
      style={{
        width,
        borderRadius: 22 * Math.max(k, 0.6),
        overflow: 'hidden',
        background: '#f6f7f4',
        boxShadow: '0 60px 120px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.12)',
        ...style,
      }}
    >
      <div
        style={{
          height: bar,
          background: '#e9ece6',
          display: 'flex',
          alignItems: 'center',
          padding: `0 ${bar * 0.4}px`,
          gap: bar * 0.18,
        }}
      >
        {['#ff5f57', '#febc2e', '#28c840'].map((color) => (
          <div
            key={color}
            style={{ width: bar * 0.28, height: bar * 0.28, borderRadius: '50%', background: color }}
          />
        ))}
        <div
          style={{
            marginLeft: bar * 0.4,
            flex: 1,
            height: bar * 0.6,
            borderRadius: bar,
            background: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            padding: `0 ${bar * 0.4}px`,
            fontFamily: FONT,
            fontSize: bar * 0.34,
            fontWeight: 600,
            color: '#5b6573',
          }}
        >
          {title}
        </div>
      </div>
      <div style={{ width, height: PAGE_HEIGHT * k, overflow: 'hidden', position: 'relative' }}>
        <div
          style={{
            width: '100%',
            height: '100%',
            transformOrigin: `${focus[0] * 100}% ${focus[1] * 100}%`,
            transform: `scale(${zoom})`,
          }}
        >
          <Img
            src={staticFile(src)}
            style={{ width: '100%', display: 'block', transform: `translateY(${-scroll * k}px)` }}
          />
          {sticky > 0 && scroll > 0 ? (
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                width: sticky * k,
                height: '100%',
                overflow: 'hidden',
              }}
            >
              <Img src={staticFile(src)} style={{ width: width, maxWidth: 'none', display: 'block' }} />
            </div>
          ) : null}
          {children ? (
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                width: PAGE_WIDTH,
                height: PAGE_HEIGHT,
                transformOrigin: '0 0',
                transform: `scale(${k})`,
              }}
            >
              {children}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
