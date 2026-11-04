// Pastille de couleur pour les statuts de commande et de lot

const TONES: Record<string, string> = {
  brouillon: 'neutral',
  envoyee: 'info',
  partiellement_recue: 'warn',
  soldee: 'ok',
  annulee: 'off',
  quarantaine: 'warn',
  libere: 'ok',
  bloque: 'danger',
  detruit: 'off',
}

export function StatusBadge({ status, label }: { status: string; label: string }) {
  return <span className={`badge badge-${TONES[status] ?? 'neutral'}`}>{label}</span>
}
