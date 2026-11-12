import React from 'react'
import { Composition } from 'remotion'
import { Demo } from './Demo'
import { FPS, HEIGHT, TOTAL, WIDTH } from './timing'

export const Root: React.FC = () => (
  <Composition id="Demo" component={Demo} durationInFrames={TOTAL} fps={FPS} width={WIDTH} height={HEIGHT} />
)
