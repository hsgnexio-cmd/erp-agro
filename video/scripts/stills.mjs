// Sort des images de contrôle de la vidéo, sans tout rendre.
// Usage : node scripts/stills.mjs 30 120 250   (numéros d'images ; résultat dans out/stills/)
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { bundle } from '@remotion/bundler'
import { renderStill, selectComposition } from '@remotion/renderer'

const frames = process.argv.slice(2).map(Number)
const root = path.resolve(import.meta.dirname, '..')
mkdirSync(path.join(root, 'out', 'stills'), { recursive: true })
const serveUrl = await bundle({ entryPoint: path.join(root, 'src', 'index.ts') })
const composition = await selectComposition({ serveUrl, id: 'Demo' })
for (const frame of frames) {
  const output = path.join(root, 'out', 'stills', `${String(frame).padStart(4, '0')}.jpg`)
  await renderStill({ composition, serveUrl, frame, output, imageFormat: 'jpeg', jpegQuality: 80, scale: 0.5 })
  console.log('ok', frame)
}
