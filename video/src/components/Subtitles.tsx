import React from 'react'
import { useCurrentFrame } from 'remotion'
import script from '../../script.json'
import { glide } from '../anim'
import { C, FONT } from '../theme'
import { SCENES, type SceneId, sec, voiceOf } from '../timing'

type Phrase = { words: string[]; first: number }

const isWord = (token: string) => /[\p{L}\p{N}]/u.test(token)
const MAX_WORDS = 9

/** Découpe le texte de la voix en courtes phrases et repère le premier mot de chacune. */
export const phrasesOf = (id: SceneId): Phrase[] => {
  const text = (script as { id: string; text: string }[]).find((line) => line.id === id)!.text
  const phrases: Phrase[] = []
  let index = 0
  for (const sentence of text.split(/(?<=[.?!])\s+|(?<=\s:)\s+/)) {
    const long = sentence.split(/\s+/).filter(isWord).length > MAX_WORDS
    for (const part of long ? sentence.split(/(?<=,)\s+/) : [sentence]) {
      // Un signe de ponctuation isolé (« ? », « : ») reste collé au mot précédent
      const words: string[] = []
      for (const token of part.split(/\s+/)) {
        if (isWord(token) || words.length === 0) words.push(token)
        else words[words.length - 1] += ` ${token}`
      }
      if (words.filter(isWord).length === 0) continue
      // Une phrase encore trop longue est coupée en deux moitiés : jamais plus d'une ligne
      const halves = words.length > MAX_WORDS ? [words.slice(0, Math.ceil(words.length / 2)), words.slice(Math.ceil(words.length / 2))] : [words]
      for (const half of halves) {
        phrases.push({ words: half, first: index })
        index += half.length
      }
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
  if (!current || frame > sec(start + voice.duration) + 6) return null
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 26, display: 'flex', justifyContent: 'center' }}>
      <div
        style={{
          opacity: glide(frame, at(current.first) - 2, 5),
          maxWidth: 1500,
          padding: '11px 30px',
          borderRadius: 14,
          background: 'rgba(15, 54, 32, 0.95)',
          boxShadow: '0 10px 30px rgba(15,54,32,0.25)',
          fontFamily: FONT,
          fontWeight: 600,
          fontSize: 33,
          whiteSpace: 'nowrap',
          display: 'flex',
          gap: '0 0.28em',
        }}
      >
        {current.words.map((text, i) => (
          <span key={i} style={{ color: frame >= at(current.first + i) ? C.cream : 'rgba(247,240,220,0.42)' }}>
            {text}
          </span>
        ))}
      </div>
    </div>
  )
}
