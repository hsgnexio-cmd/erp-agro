import { CornerDownLeft, Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { apiRequest } from '../api/client'

type Result = { type: string; label: string; detail: string; url: string }

const TYPE_LABELS: Record<string, string> = {
  lot: 'Lot',
  article: 'Article',
  client: 'Enseigne',
  fournisseur: 'Fournisseur',
  of: 'OF',
}

/** Recherche globale (Ctrl+K) : numéro de lot, article, enseigne, fournisseur ou OF. */
export function CommandPalette({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const input = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Result[]>([])
  const [active, setActive] = useState(0)
  const [searched, setSearched] = useState('')

  useEffect(() => {
    input.current?.focus()
  }, [])

  // La recherche part 200 ms après la dernière frappe ; une réponse en retard est ignorée
  useEffect(() => {
    const text = query.trim()
    if (text.length < 2) return
    let cancelled = false
    const timer = setTimeout(() => {
      apiRequest<{ results: Result[] }>(`/api/pilotage/search/?q=${encodeURIComponent(text)}`)
        .then((data) => {
          if (cancelled) return
          setResults(data.results)
          setActive(0)
          setSearched(text)
        })
        .catch(() => {
          if (!cancelled) setResults([])
        })
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [query])

  const shown = query.trim().length < 2 ? [] : results

  function open(result: Result) {
    onClose()
    void navigate(result.url)
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === 'Escape') onClose()
    else if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActive((index) => Math.min(index + 1, shown.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActive((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter' && shown[active]) open(shown[active])
  }

  return (
    <div className="palette-backdrop" onClick={onClose}>
      <div
        className="palette"
        role="dialog"
        aria-modal="true"
        aria-label="Recherche globale"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        <div className="palette-input">
          <Search size={18} aria-hidden="true" />
          <input
            ref={input}
            type="search"
            aria-label="Rechercher dans l'ERP"
            placeholder="Numéro de lot, article, enseigne, fournisseur, OF…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <kbd>Échap</kbd>
        </div>
        {shown.length > 0 ? (
          <ul className="palette-results">
            {shown.map((result, index) => (
              <li key={`${result.type}-${result.url}-${result.label}`}>
                <button
                  type="button"
                  className={index === active ? 'palette-result active' : 'palette-result'}
                  onMouseEnter={() => setActive(index)}
                  onClick={() => open(result)}
                >
                  <span className="palette-type">{TYPE_LABELS[result.type] ?? result.type}</span>
                  <strong>{result.label}</strong>
                  <span className="palette-detail">{result.detail}</span>
                  {index === active && <CornerDownLeft size={14} aria-hidden="true" />}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="palette-empty">
            {query.trim().length < 2
              ? 'Tape au moins 2 caractères. Exemples : LR-2611, crème, ENS2, OF-2026.'
              : searched === query.trim()
                ? 'Aucun résultat.'
                : 'Recherche…'}
          </p>
        )}
      </div>
    </div>
  )
}
