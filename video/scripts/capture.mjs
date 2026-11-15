// Captures d'écran de l'ERP pour la vidéo, par le protocole DevTools d'Edge ou de Chrome
// (aucune dépendance). Voir video/README.md pour le lancement.
//
// Usage : node capture.mjs <port-devtools> <base-url> <sessions.json> <dossier-sortie> <plan.json>
//   sessions.json : { "admin": "<sessionid>", ... }
//   plan.json     : liste d'écrans { session, path, wait, steps: [...] }
//
// Étapes possibles (dans l'ordre où elles sont écrites dans le plan) :
//   { "run": "<JavaScript>" }                 exécute du code dans la page
//   { "click": "<cible>" }                    vrai clic de souris au centre de l'élément
//   { "hover": "<cible>" }                    survol
//   { "key": "Control+k" | "Enter" | ... }    touche du clavier
//   { "type": "texte", "frames": "prefixe" }  frappe ; une image par caractère si « frames »
//   { "select": "<cible>", "value": "4" }  choix dans une liste déroulante
//   { "scroll": 600 }                         fait défiler la page (pixels)
//   { "shot": "fichier.jpg", "tall": true }   capture (page entière si « tall »)
//   { "measure": { "nom": "<cible>" } }       position des éléments, écrite dans rects.json
//   chaque étape peut avoir "wait" (millisecondes d'attente après l'action)
// Une cible est un sélecteur CSS, ou « texte:Libellé » (bouton, lien, onglet, cellule…),
// éventuellement « texte:Libellé@2 » pour la 2e occurrence.
import { existsSync, readFileSync, writeFileSync } from 'node:fs'

const [port, base, sessionsFile, outDir, planFile] = process.argv.slice(2)
const read = (file) => JSON.parse(readFileSync(file, 'utf8').replace(/^﻿/, ''))
const sessions = read(sessionsFile)
const plan = read(planFile)
const only = process.env.CAPTURE_ONLY?.split(',')
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const WIDTH = Number(process.env.CAPTURE_WIDTH ?? 1440)
const HEIGHT = 900
const SCALE = Number(process.env.CAPTURE_SCALE ?? 2)
const rectsFile = `${outDir}/rects.json`
const rects = existsSync(rectsFile) ? read(rectsFile) : {}

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
const evaluate = async (expression) => {
  const reply = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (reply.result?.exceptionDetails) {
    throw new Error(`${expression}\n${JSON.stringify(reply.result.exceptionDetails.exception?.description)}`)
  }
  return reply.result?.result?.value
}

const viewport = (height = HEIGHT) =>
  send('Emulation.setDeviceMetricsOverride', { width: WIDTH, height, deviceScaleFactor: SCALE, mobile: false })

await send('Page.enable')
await send('Network.enable')
await viewport()
await send('Emulation.setScrollbarsHidden', { hidden: true })
const host = new URL(base).hostname

// Fonction installée dans la page : retrouve un élément d'après une cible
const FIND = `(target) => {
  if (!target.startsWith('texte:')) return document.querySelector(target)
  const [label, rank] = target.slice(6).split('@')
  const all = [...document.querySelectorAll('button, a, [role=tab], summary, label, th, td, h1, h2, h3, strong, span, option, li')]
  const visible = all.filter((el) => el.getClientRects().length > 0)
  const exact = visible.filter((el) => el.textContent.trim() === label)
  const found = exact.length > 0 ? exact : visible.filter((el) => el.textContent.includes(label))
  // Le plus petit élément qui contient le libellé
  const smallest = found.filter((el) => !found.some((other) => other !== el && el.contains(other)))
  return smallest[Number(rank ?? 1) - 1] ?? null
}`

const rectOf = async (target) => {
  const rect = await evaluate(`(() => {
    const el = (${FIND})(${JSON.stringify(target)})
    if (!el) return null
    const r = el.getBoundingClientRect()
    return [Math.round(r.x), Math.round(r.y + window.scrollY), Math.round(r.width), Math.round(r.height), Math.round(window.scrollY)]
  })()`)
  if (!rect) throw new Error(`Élément introuvable : ${target}`)
  return rect
}

const mouse = (type, x, y, extra = {}) => send('Input.dispatchMouseEvent', { type, x, y, ...extra })
const pointAt = async (target) => {
  await evaluate(`(${FIND})(${JSON.stringify(target)})?.scrollIntoView({ block: 'nearest' })`)
  const [x, y, width, height, scrollY] = await rectOf(target)
  return [x + width / 2, y - scrollY + height / 2]
}

const KEYS = { Enter: 13, Escape: 27, ArrowDown: 40, ArrowUp: 38, Tab: 9 }
const press = async (combo) => {
  const parts = combo.split('+')
  const key = parts.pop()
  const modifiers = (parts.includes('Control') ? 2 : 0) + (parts.includes('Shift') ? 8 : 0)
  const code = KEYS[key] ?? key.toUpperCase().charCodeAt(0)
  const event = {
    key, modifiers, windowsVirtualKeyCode: code,
    code: KEYS[key] ? key : `Key${key.toUpperCase()}`,
    ...(key === 'Enter' ? { text: '\r' } : {}),
  }
  await send('Input.dispatchKeyEvent', { type: 'keyDown', ...event })
  await send('Input.dispatchKeyEvent', { type: 'keyUp', ...event })
}

let last = null
const shot = async (file, tall = false) => {
  if (tall) {
    // Page entière : la fenêtre prend la hauteur du contenu, le temps de la capture
    const height = await evaluate('Math.min(4600, Math.max(900, document.documentElement.scrollHeight))')
    await viewport(height)
    await sleep(700)
  }
  const result = await send('Page.captureScreenshot', { format: 'jpeg', quality: 88 })
  writeFileSync(`${outDir}/${file}`, Buffer.from(result.result.data, 'base64'))
  if (tall) await viewport()
  last = file
  console.log('ok', file)
}

let current = null
for (const screen of plan) {
  if (only && !only.includes(screen.name)) continue
  if (screen.session !== current) {
    current = screen.session
    await send('Network.setCookie', { name: 'sessionid', value: sessions[current], domain: host, path: '/' })
  }
  await send('Page.navigate', { url: base + screen.path })
  await sleep(screen.wait ?? 4000)
  for (const step of screen.steps ?? []) {
    try {
      if (step.run) await evaluate(step.run)
      if (step.hover) await mouse('mouseMoved', ...(await pointAt(step.hover)))
      if (step.click) {
        const [x, y] = await pointAt(step.click)
        await mouse('mouseMoved', x, y)
        await mouse('mousePressed', x, y, { button: 'left', clickCount: 1 })
        await mouse('mouseReleased', x, y, { button: 'left', clickCount: 1 })
      }
      if (step.select) {
        // Choix dans une liste déroulante, comme le ferait l'utilisateur (React reçoit l'événement)
        await evaluate(`(() => { const s = (${FIND})(${JSON.stringify(step.select)}); if (!s) throw new Error('liste introuvable'); Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(s, ${JSON.stringify(step.value)}); s.dispatchEvent(new Event('change', { bubbles: true })) })()`)
      }
      if (step.key) await press(step.key)
      if (step.scroll !== undefined) await evaluate(`window.scrollTo(0, ${step.scroll})`)
      if (step.type) {
        const text = step.type
        const name = (i) => `${step.frames}-${String(i).padStart(2, '0')}.jpg`
        if (step.frames) await shot(name(0))
        for (let i = 0; i < text.length; i += 1) {
          await send('Input.insertText', { text: text[i] })
          await sleep(step.frames ? (step.delay ?? 150) : 30)
          if (step.frames && (i < text.length - 1 || !step.settle)) await shot(name(i + 1))
        }
        if (step.frames && step.settle) {
          // Dernière image après la réponse du serveur (résultats de recherche affichés)
          await sleep(step.settle)
          await shot(name(text.length))
        }
      }
      await sleep(step.wait ?? 300)
      if (step.shot) await shot(step.shot, step.tall)
      if (step.measure) {
        const key = step.as ?? last
        rects[key] = rects[key] ?? {}
        for (const [name, target] of Object.entries(step.measure)) {
          try {
            rects[key][name] = await rectOf(target)
          } catch (error) {
            console.error(`  mesure absente (${key}) :`, error.message)
          }
        }
      }
    } catch (error) {
      console.error(`ÉCHEC ${screen.name ?? screen.path} :`, JSON.stringify(step), '\n ', error.message)
    }
  }
}
writeFileSync(rectsFile, JSON.stringify(rects, null, 1))
ws.close()
