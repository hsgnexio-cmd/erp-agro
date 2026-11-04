// Mise en forme pour l'affichage (en français)

export const TEMPERATURE_LABELS: Record<string, string> = {
  ambiant: 'Ambiant',
  froid_positif: 'Froid positif (0 à 4 °C)',
  froid_negatif: 'Froid négatif (-18 °C)',
}

export const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrateur',
  direction: 'Direction',
  acheteur: 'Acheteur',
  magasinier: 'Magasinier',
  production: 'Production',
  qualite: 'Qualité',
  commercial: 'Commercial',
}

/** "53.3333" → "53,3333" ; "70.00" → "70" */
export function formatDecimal(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  return Number(value).toLocaleString('fr-FR', { maximumFractionDigits: 4 })
}

export function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('fr-FR')
}

export const yesNo = (value: boolean) => (value ? 'Oui' : 'Non')

export function formatDateTime(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

export function formatMoney(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  return Number(value).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })
}

/** Date du jour au format AAAA-MM-JJ (pour les champs de date) */
export function todayIso(): string {
  const now = new Date()
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 10)
}

export const LOT_STATUS_LABELS: Record<string, string> = {
  quarantaine: 'Quarantaine',
  libere: 'Libéré',
  bloque: 'Bloqué',
  detruit: 'Détruit',
}

/** SSCC lisible : (00) puis extension, préfixe GS1, numéro de série et clé, comme sur l'étiquette. */
export const formatSscc = (sscc: string) =>
  `(00) ${sscc.slice(0, 1)} ${sscc.slice(1, 8)} ${sscc.slice(8, 17)} ${sscc.slice(17)}`
