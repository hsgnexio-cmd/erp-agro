import React from 'react'
import { Audio, Sequence, staticFile } from 'remotion'

export type SfxName = 'clic' | 'touche' | 'glisse' | 'carton' | 'validation' | 'alerte'

// Bruitages volontairement discrets (fabriqués par scripts/sfx.mjs)
const LEVEL: Record<SfxName, number> = {
  clic: 0.5,
  touche: 0.28,
  glisse: 0.5,
  carton: 0.55,
  validation: 0.22,
  alerte: 0.4,
}

/** Joue un bruitage à l'image `at` de la scène. */
export const Sfx: React.FC<{ at: number; name: SfxName; volume?: number }> = ({ at, name, volume = 1 }) => (
  <Sequence from={Math.max(0, Math.round(at))} durationInFrames={40} layout="none" name={`son ${name}`}>
    <Audio src={staticFile(`sfx/${name}.wav`)} volume={LEVEL[name] * volume} />
  </Sequence>
)
