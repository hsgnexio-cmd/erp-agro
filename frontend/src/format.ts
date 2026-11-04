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
