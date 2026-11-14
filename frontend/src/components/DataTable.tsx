import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import { type ReactNode, useMemo, useState } from 'react'

type SortValue = string | number | null | undefined

export type DataColumn<T> = {
  id: string
  header: string
  /** Contenu de la cellule. */
  cell: (row: T) => ReactNode
  /** Valeur de tri ; sans elle, la colonne n'est pas triable. */
  sortValue?: (row: T) => SortValue
  /** Chiffres, poids, euros, pourcentages : alignés à droite, à chasse fixe. */
  numeric?: boolean
  width?: string
}

export type BulkAction<T> = {
  label: string
  onRun: (rows: T[]) => void
  /** Action destructive ou bloquante (bouton rouge). */
  danger?: boolean
}

type SortRule = { id: string; descending: boolean }

/** Comparaison d'un texte ou d'un nombre ; les valeurs vides vont à la fin. */
function compare(a: SortValue, b: SortValue): number {
  const emptyA = a === null || a === undefined || a === ''
  const emptyB = b === null || b === undefined || b === ''
  if (emptyA || emptyB) return emptyA === emptyB ? 0 : emptyA ? 1 : -1
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return String(a).localeCompare(String(b), 'fr', { numeric: true, sensitivity: 'base' })
}

/**
 * Tableau de données : en-têtes collants, tri par colonne (Maj + clic pour trier sur plusieurs
 * colonnes), cases à cocher avec barre d'actions groupées, chiffres alignés à droite.
 *
 * Le tri et la sélection portent sur les lignes reçues (`rows`) : la pagination reste gérée par
 * l'écran, comme aujourd'hui.
 */
export function DataTable<T>({
  rows,
  columns,
  rowKey,
  caption,
  bulkActions,
  onRowClick,
  empty = 'Aucune ligne.',
  maxHeight,
}: {
  rows: T[]
  columns: DataColumn<T>[]
  rowKey: (row: T) => string | number
  /** Description du tableau, lue par les lecteurs d'écran. */
  caption: string
  /** Avec des actions groupées, chaque ligne a une case à cocher. */
  bulkActions?: BulkAction<T>[]
  /** Clic sur une ligne (par exemple pour ouvrir sa fiche dans un tiroir). */
  onRowClick?: (row: T) => void
  empty?: string
  /** Hauteur maximale (ex. « 60vh ») : le corps défile, les en-têtes restent visibles. */
  maxHeight?: string
}) {
  const [sort, setSort] = useState<SortRule[]>([])
  const [selected, setSelected] = useState<Set<string | number>>(new Set())
  const selectable = Boolean(bulkActions?.length)

  const sorted = useMemo(() => {
    const rules = sort
      .map((rule) => ({ ...rule, column: columns.find((column) => column.id === rule.id) }))
      .filter((rule) => rule.column?.sortValue)
    if (rules.length === 0) return rows
    return [...rows].sort((a, b) => {
      for (const rule of rules) {
        const result = compare(rule.column!.sortValue!(a), rule.column!.sortValue!(b))
        if (result !== 0) return rule.descending ? -result : result
      }
      return 0
    })
  }, [rows, columns, sort])

  // Une ligne disparue de la liste (filtre, page suivante) ne reste pas sélectionnée
  const keys = useMemo(() => new Set(rows.map(rowKey)), [rows, rowKey])
  const selectedRows = sorted.filter((row) => selected.has(rowKey(row)))
  const allSelected = rows.length > 0 && selectedRows.length === rows.length

  function toggleSort(column: DataColumn<T>, additive: boolean) {
    setSort((current) => {
      const existing = current.find((rule) => rule.id === column.id)
      // Croissant, puis décroissant, puis plus de tri sur cette colonne
      const next: SortRule | null = !existing
        ? { id: column.id, descending: false }
        : existing.descending
          ? null
          : { id: column.id, descending: true }
      const others = additive ? current.filter((rule) => rule.id !== column.id) : []
      if (!next) return others
      return additive && existing
        ? current.map((rule) => (rule.id === column.id ? next : rule))
        : [...others, next]
    })
  }

  function toggleRow(key: string | number) {
    setSelected((current) => {
      const next = new Set([...current].filter((item) => keys.has(item)))
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  function toggleAll() {
    setSelected(allSelected ? new Set() : new Set(rows.map(rowKey)))
  }

  return (
    <div className="datatable">
      <div className="table-wrapper datatable-scroll" style={maxHeight ? { maxHeight } : undefined}>
        <table>
          <caption className="visually-hidden">{caption}</caption>
          <thead>
            <tr>
              {selectable && (
                <th className="datatable-check">
                  <input
                    type="checkbox"
                    aria-label="Tout sélectionner"
                    checked={allSelected}
                    onChange={toggleAll}
                  />
                </th>
              )}
              {columns.map((column) => {
                const index = sort.findIndex((rule) => rule.id === column.id)
                const rule = sort[index]
                const direction = !rule ? 'none' : rule.descending ? 'descending' : 'ascending'
                return (
                  <th
                    key={column.id}
                    scope="col"
                    className={column.numeric ? 'num' : undefined}
                    style={column.width ? { width: column.width } : undefined}
                    aria-sort={column.sortValue ? direction : undefined}
                  >
                    {column.sortValue ? (
                      <button
                        type="button"
                        className="datatable-sort"
                        title="Trier (Maj + clic : ajouter un second tri)"
                        onClick={(event) => toggleSort(column, event.shiftKey)}
                      >
                        {column.header}
                        {!rule ? (
                          <ArrowUpDown size={13} aria-hidden="true" className="datatable-sort-idle" />
                        ) : rule.descending ? (
                          <ArrowDown size={13} aria-hidden="true" />
                        ) : (
                          <ArrowUp size={13} aria-hidden="true" />
                        )}
                        {sort.length > 1 && rule && <sup>{index + 1}</sup>}
                      </button>
                    ) : (
                      column.header
                    )}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td className="datatable-empty" colSpan={columns.length + (selectable ? 1 : 0)}>
                  {empty}
                </td>
              </tr>
            ) : (
              sorted.map((row) => {
                const key = rowKey(row)
                const checked = selected.has(key)
                return (
                  <tr
                    key={key}
                    className={[checked ? 'selected' : '', onRowClick ? 'clickable' : '']
                      .filter(Boolean)
                      .join(' ')}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                  >
                    {selectable && (
                      <td className="datatable-check" onClick={(event) => event.stopPropagation()}>
                        <input
                          type="checkbox"
                          aria-label="Sélectionner la ligne"
                          checked={checked}
                          onChange={() => toggleRow(key)}
                        />
                      </td>
                    )}
                    {columns.map((column) => (
                      <td key={column.id} className={column.numeric ? 'num' : undefined}>
                        {column.cell(row)}
                      </td>
                    ))}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
      {selectable && selectedRows.length > 0 && (
        <div className="bulk-bar" role="region" aria-label="Actions sur la sélection">
          <strong>
            {selectedRows.length} ligne{selectedRows.length > 1 ? 's' : ''} sélectionnée
            {selectedRows.length > 1 ? 's' : ''}
          </strong>
          {bulkActions!.map((action) => (
            <button
              key={action.label}
              type="button"
              className={action.danger ? 'danger' : 'secondary'}
              onClick={() => action.onRun(selectedRows)}
            >
              {action.label}
            </button>
          ))}
          <button type="button" className="bulk-clear" onClick={() => setSelected(new Set())}>
            Tout désélectionner
          </button>
        </div>
      )}
    </div>
  )
}
