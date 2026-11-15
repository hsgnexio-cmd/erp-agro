import { loadFont as loadOutfit } from '@remotion/google-fonts/Outfit'
import { loadFont as loadMono } from '@remotion/google-fonts/JetBrainsMono'

export const FONT = loadOutfit('normal', {
  weights: ['400', '500', '600', '700', '800'],
  subsets: ['latin'],
}).fontFamily
export const MONO = loadMono('normal', { weights: ['500', '700'], subsets: ['latin'] }).fontFamily

// Couleurs de la charte de l'ERP (frontend/src/index.css) et accents de la vidéo
export const C = {
  paper: '#F6F7F4',
  forest: '#164A2C',
  forestDark: '#0F3620',
  cream: '#F7F0DC',
  accent: '#B6F36A',
  ink: '#18212B',
  muted: '#56616E',
  border: '#E2E5DF',
  red: '#C0392B',
  amber: '#D98A1F',
  white: '#FFFFFF',
}
