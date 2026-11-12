// Estime le tempo (BPM) et l'instant du premier temps d'un WAV mono 16 bits.
import { readFileSync } from 'node:fs'
const buf = readFileSync(process.argv[2])
const dataAt = buf.indexOf('data') + 8
const sr = buf.readUInt32LE(24)
const pcm = new Int16Array(buf.buffer, buf.byteOffset + dataAt, Math.floor((buf.length - dataAt) / 2))
const hop = 128 // ~11,6 ms
const n = Math.floor(pcm.length / hop)
const env = new Float32Array(n)
for (let i = 0; i < n; i++) { let s = 0; for (let j = 0; j < hop; j++) { const v = pcm[i * hop + j]; s += v * v } env[i] = Math.sqrt(s / hop) }
// Flux d'énergie (montées seulement)
const flux = new Float32Array(n)
for (let i = 1; i < n; i++) flux[i] = Math.max(0, env[i] - env[i - 1])
const fps = sr / hop
let best = { bpm: 0, score: -1 }
for (let bpm = 80; bpm <= 180; bpm += 0.25) {
  const lag = (60 / bpm) * fps
  let s = 0
  for (let i = 0; i + lag * 4 < n; i++) { s += flux[i] * (flux[Math.round(i + lag)] + 0.5 * flux[Math.round(i + 2 * lag)] + 0.25 * flux[Math.round(i + 4 * lag)]) }
  if (s > best.score) best = { bpm, score: s }
}
const period = (60 / best.bpm) * fps
let bestPhase = 0, bestS = -1
for (let p = 0; p < period; p += 0.5) { let s = 0; for (let k = 0; p + k * period < n; k++) s += flux[Math.round(p + k * period)]; if (s > bestS) { bestS = s; bestPhase = p } }
// Énergie moyenne par tranche de 4 s (pour repérer l'entrée du rythme)
const sec = []
for (let t = 0; t < n / fps; t += 4) { let s = 0, c = 0; for (let i = Math.floor(t * fps); i < Math.min(n, (t + 4) * fps); i++) { s += env[i]; c++ } sec.push(Math.round(s / c)) }
console.log(JSON.stringify({ bpm: best.bpm, firstBeat: +(bestPhase / fps).toFixed(3), energyPer4s: sec }))
