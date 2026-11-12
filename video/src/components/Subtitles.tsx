import React from 'react'
import { useCurrentFrame } from 'remotion'
import script from '../../script.json'
import { glide } from '../anim'
import { C, FONT } from '../theme'
import { SCENES, type SceneId, sec, voiceOf } from '../timing'

type Phrase = { words: string[]; first: number }

const isWord = (token: string) => /[\p{L}\p{N}]/u.test(token)

/** Découpe le texte de la voix en courtes phrases et repère le premier mot de chacune. */
const phrasesOf = (id: SceneId): Phrase[] => {
  const text = (script as { id: string; text: string }[]).find((line) => line.id === id)!.text
  const phrases: Phrase[] = []
  let index = 0
  for (const sentence of text.split(/(?<=[.?!:])\s+/)) {
    const long = sentence.split(/\s+/).filter(isWord).length > 8
    for (const part of long ? sentence.split(/(?<=,)\s+/) : [sentence]) {
      const tokens = part.split(/\s+/)
      const count = tokens.filter(isWord).length
      if (count === 0) continue
      // Un signe de ponctuation isolé (« ? », « : ») reste collé au mot précédent
      const words: string[] = []
      for (const token of tokens) {
        if (isWord(token) || words.length === 0) words.push(token)
        else words[words.length - 1] += ` ${token}`
      }
      phrases.push({ words, first: index })
      index += count
    }
  }
  return phrases
}

/** Sous-titres de la voix, mot à mot (pour les vidéos regardées sans le son). */
export const Subtitles: React.FC<{ id: SceneId }> = ({ id }) => {
  const frame = useCurrentFrame()
  const voice = voiceOf(id)
  const start = SCENES[id].voiceAt
  const at = (index: number) => sec(start + voice.words[Math.min(index, voice.words.length - 1)].t)
  const current = phrasesOf(id).findLast((phrase) => frame >= at(phrase.first) - 2)
  if (!current || frame > sec(start + voice.duration) + 8) return null
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 54,
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          opacity: glide(frame, at(current.first) - 2, 5),
          padding: '14px 34px',
          borderRadius: 18,
          background: 'rgba(4, 12, 7, 0.8)',
          border: '1px solid rgba(255,255,255,0.14)',
          fontFamily: FONT,
          fontWeight: 600,
          fontSize: 38,
          display: 'flex',
          gap: '0 0.28em',
        }}
      >
        {current.words.map((text, i) => (
          <span
            key={i}
            style={{ color: frame >= at(current.first + i) ? C.white : 'rgba(255,255,255,0.38)' }}
          >
            {text}
          </span>
        ))}
      </div>
    </div>
  )
}
