import { loadFont as loadOutfit } from '@remotion/google-fonts/Outfit'
import { loadFont as loadMono } from '@remotion/google-fonts/JetBrainsMono'

export const FONT = loadOutfit('normal', {
  weights: ['400', '600', '800', '900'],
  subsets: ['latin'],
}).fontFamily
export const MONO = loadMono('normal', { weights: ['500', '700'], subsets: ['latin'] }).fontFamily

// Couleurs de l'ERP (frontend/src/index.css) et accents de la vidéo
export const C = {
  brand: '#2f6b3a',
  brandDark: '#1e5128',
  brandLight: '#dcefdc',
  night: '#06120a',
  deep: '#0d2414',
  lime: '#b6f36a',
  cream: '#fdf0d5',
  red: '#ff4d4f',
  redDark: '#8a1c1c',
  white: '#ffffff',
  muted: 'rgba(255,255,255,0.62)',
}
