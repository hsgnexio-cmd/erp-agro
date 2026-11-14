// Captures d'écran de l'ERP pour la vidéo, par le protocole DevTools d'Edge ou de Chrome
// (aucune dépendance). Voir video/README.md pour le lancement.
//
// Usage : node capture.mjs <port-devtools> <base-url> <sessions.json> <dossier-sortie> <plan.json>
//   sessions.json : { "direction": "<sessionid>", "qualite": "...", ... }
//   plan.json     : liste d'étapes { session, path, file, wait, fullPage, typing, run }
import { readFileSync, writeFileSync } from 'node:fs'

const [port, base, sessionsFile, outDir, planFile] = process.argv.slice(2)
const read = (file) => JSON.parse(readFileSync(file, 'utf8').replace(/^﻿/, ''))
const sessions = read(sessionsFile)
const plan = read(planFile)
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const WIDTH = Number(process.env.CAPTURE_WIDTH ?? 1440)
const HEIGHT = 900
const SCALE = Number(process.env.CAPTURE_SCALE ?? 2)

const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
const ws = new WebSocket(targets.find((t) => t.type === 'page').webSocketDebuggerUrl)
await new Promise((r) => ws.addEventListener('open', r))
let id = 0
const pending = new Map()
ws.addEventListener('message', (e) => {
  const msg = JSON.parse(e.data)
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg)
    pending.delete(msg.id)
  }
})
const send = (method, params = {}) =>
  new Promise((resolve) => {
    id += 1
    pending.set(id, resolve)
    ws.send(JSON.stringify({ id, method, params }))
  })

await send('Page.enable')
await send('Network.enable')
await send('Emulation.setDeviceMetricsOverride', {
  width: WIDTH, height: HEIGHT, deviceScaleFactor: SCALE, mobile: false,
})
await send('Emulation.setScrollbarsHidden', { hidden: true })
const host = new URL(base).hostname

const shot = async (file, fullPage = false) => {
  const params = { format: 'jpeg', quality: 88 }
  if (fullPage) {
    const metrics = await send('Page.getLayoutMetrics')
    const { width, height } = metrics.result.cssContentSize
    params.clip = { x: 0, y: 0, width, height: Math.min(height, 4200), scale: 1 }
    params.captureBeyondViewport = true
  }
  const result = await send('Page.captureScreenshot', params)
  writeFileSync(`${outDir}/${file}`, Buffer.from(result.result.data, 'base64'))
  console.log('ok', file)
}

let current = null
for (const step of plan) {
  if (step.session !== current) {
    current = step.session
    await send('Network.setCookie', {
      name: 'sessionid', value: sessions[current], domain: host, path: '/',
    })
  }
  await send('Page.navigate', { url: base + step.path })
  await sleep(step.wait ?? 4000)
  if (step.typing) {
    // Saisie caractère par caractère dans le premier champ texte, une image par caractère
    const { text, prefix } = step.typing
    await send('Runtime.evaluate', {
      expression: "document.querySelector('main input[type=text], main input:not([type])').focus()",
    })
    await shot(`${prefix}-00.jpg`)
    for (let i = 0; i < text.length; i += 1) {
      await send('Input.insertText', { text: text[i] })
      await sleep(120)
      await shot(`${prefix}-${String(i + 1).padStart(2, '0')}.jpg`)
    }
    const enter = { key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' }
    await send('Input.dispatchKeyEvent', { type: 'keyDown', ...enter })
    await send('Input.dispatchKeyEvent', { type: 'keyUp', ...enter })
    await sleep(step.typing.wait ?? 5000)
  }
  if (step.run) {
    // Action avant la capture (ex. cliquer sur un bouton) : expression JavaScript de la page
    await send('Runtime.evaluate', { expression: step.run })
    await sleep(step.runWait ?? 2000)
  }
  if (step.file) await shot(step.file, step.fullPage)
}
ws.close()
