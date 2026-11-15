// Fabrique les bruitages d'interface de la vidéo (clic, frappe, tiroir, carton, validation)
// par simple calcul : aucun fichier téléchargé, aucune dépendance.
// Usage : node scripts/sfx.mjs   (résultat dans public/sfx/*.wav)
import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'

const RATE = 44100
const out = path.resolve(import.meta.dirname, '..', 'public', 'sfx')
mkdirSync(out, { recursive: true })

// Bruit reproductible (même fichier à chaque lancement)
let seed = 12345
const noise = () => {
  seed = (seed * 1664525 + 1013904223) % 4294967296
  return seed / 2147483648 - 1
}

/** Écrit un fichier WAV mono 16 bits à partir d'une fonction du temps (valeurs entre -1 et 1). */
const write = (name, seconds, sample) => {
  const count = Math.round(seconds * RATE)
  const data = Buffer.alloc(44 + count * 2)
  data.write('RIFF', 0)
  data.writeUInt32LE(36 + count * 2, 4)
  data.write('WAVEfmt ', 8)
  data.writeUInt32LE(16, 16)
  data.writeUInt16LE(1, 20)
  data.writeUInt16LE(1, 22)
  data.writeUInt32LE(RATE, 24)
  data.writeUInt32LE(RATE * 2, 28)
  data.writeUInt16LE(2, 32)
  data.writeUInt16LE(16, 34)
  data.write('data', 36)
  data.writeUInt32LE(count * 2, 40)
  for (let i = 0; i < count; i += 1) {
    const value = Math.max(-1, Math.min(1, sample(i / RATE, i)))
    data.writeInt16LE(Math.round(value * 32767), 44 + i * 2)
  }
  writeFileSync(path.join(out, `${name}.wav`), data)
  console.log('ok', name)
}

const sine = (frequency, t) => Math.sin(2 * Math.PI * frequency * t)

// Clic de souris : un petit « toc » sec
write('clic', 0.09, (t) => 0.7 * Math.exp(-t * 90) * (sine(1500, t) * 0.6 + sine(320, t) * 0.5 + noise() * Math.exp(-t * 400) * 0.6))

// Touche de clavier : plus doux et plus court
write('touche', 0.06, (t) => 0.45 * Math.exp(-t * 130) * (sine(2100, t) * 0.4 + noise() * Math.exp(-t * 300) * 0.8))

// Tiroir ou changement d'écran : souffle filtré qui monte puis s'éteint
let low = 0
write('glisse', 0.42, (t) => {
  const envelope = Math.sin(Math.PI * Math.min(1, t / 0.42)) ** 2
  const cutoff = 0.04 + 0.22 * (t / 0.42)
  low += cutoff * (noise() - low)
  return 0.8 * envelope * low
})

// Carton de titre : note grave et ronde
write('carton', 0.9, (t) => {
  const attack = Math.min(1, t / 0.015)
  return 0.6 * attack * Math.exp(-t * 4.5) * (sine(98, t) + 0.5 * sine(196, t) + 0.2 * sine(392, t)) / 1.7
})

// Validation : deux notes claires (quinte), pour un chiffre clé ou une action réussie
write('validation', 0.7, (t) => {
  const note = (frequency, start) => (t < start ? 0 : Math.exp(-(t - start) * 7) * sine(frequency, t - start))
  return 0.4 * (note(880, 0) + note(1318.5, 0.09))
})

// Alerte : note basse doublée, pour le lot contaminé
write('alerte', 0.8, (t) => {
  const note = (start) => (t < start ? 0 : Math.exp(-(t - start) * 9) * (sine(220, t - start) + 0.6 * sine(233, t - start)))
  return 0.4 * (note(0) + note(0.22))
})
