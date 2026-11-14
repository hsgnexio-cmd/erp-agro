import { useState } from 'react'
import type { Paginated, Supplier } from '../api/types'
import { type DataColumn, DataTable } from '../components/DataTable'
import { Drawer } from '../components/Drawer'
import { formatDate } from '../format'
import { useApi } from '../hooks/useApi'

const categories = (supplier: Supplier) => supplier.category_codes.join(', ') || 'Emballages'

function Audit({ supplier }: { supplier: Supplier }) {
  return supplier.audited ? (
    <span className="badge badge-ok">Audité le {formatDate(supplier.last_audit_date)}</span>
  ) : (
    <span className="badge badge-warn">Non audité</span>
  )
}

const COLUMNS: DataColumn<Supplier>[] = [
  { id: 'code', header: 'Code', sortValue: (s) => s.code, cell: (s) => s.code },
  { id: 'name', header: 'Raison sociale', sortValue: (s) => s.name, cell: (s) => s.name },
  { id: 'city', header: 'Ville', sortValue: (s) => s.city, cell: (s) => s.city || '—' },
  { id: 'categories', header: 'Catégories', sortValue: categories, cell: categories },
  {
    id: 'lead_time',
    header: 'Délai',
    numeric: true,
    sortValue: (s) => s.lead_time_days,
    cell: (s) => `${s.lead_time_days} j`,
  },
  {
    id: 'audit',
    header: 'Audit',
    sortValue: (s) => s.last_audit_date,
    cell: (s) => <Audit supplier={s} />,
  },
]

export function SuppliersPage() {
  const [search, setSearch] = useState('')
  const [opened, setOpened] = useState<Supplier | null>(null)
  const params = new URLSearchParams()
  if (search) params.set('search', search)
  const { data, error } = useApi<Paginated<Supplier>>(`/api/referentiel/suppliers/?${params}`)

  return (
    <section>
      <h1>Fournisseurs</h1>
      <p className="page-intro">
        Seul un fournisseur audité peut recevoir une commande. Clique sur une ligne pour voir sa fiche.
      </p>
      <div className="filters">
        <input
          type="search"
          placeholder="Rechercher un fournisseur"
          aria-label="Rechercher"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <DataTable
          caption="Fournisseurs"
          rows={data.results}
          columns={COLUMNS}
          rowKey={(supplier) => supplier.id}
          onRowClick={setOpened}
          empty="Aucun fournisseur ne correspond."
        />
      )}
      {opened && (
        <Drawer open onClose={() => setOpened(null)} title={opened.code} subtitle={opened.name}>
          <dl className="details drawer-details">
            <dt>Ville</dt>
            <dd>
              {opened.city || '—'}
              {opened.country && ` (${opened.country})`}
            </dd>
            <dt>Catégories fournies</dt>
            <dd>{categories(opened)}</dd>
            <dt>Délai d'approvisionnement</dt>
            <dd>{opened.lead_time_days} jour(s) ouvré(s)</dd>
            <dt>Audit</dt>
            <dd>
              <Audit supplier={opened} />
            </dd>
            <dt>E-mail</dt>
            <dd>{opened.email || '—'}</dd>
            <dt>Téléphone</dt>
            <dd>{opened.phone || '—'}</dd>
            <dt>Actif</dt>
            <dd>{opened.active ? 'Oui' : 'Non'}</dd>
          </dl>
        </Drawer>
      )}
    </section>
  )
}
