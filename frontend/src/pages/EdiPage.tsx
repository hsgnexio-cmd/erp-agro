import { ExternalLink } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { apiPost, errorMessages } from '../api/client'
import type { EdiMessage } from '../api/sales'
import type { Paginated } from '../api/types'
import { useAuth } from '../auth/context'
import { SALES_ROLES, hasRole } from '../auth/roles'
import { type DataColumn, DataTable } from '../components/DataTable'
import { Drawer } from '../components/Drawer'
import { ErrorList } from '../components/ErrorList'
import { StatusBadge } from '../components/StatusBadge'
import { formatDateTime } from '../format'
import { useApi } from '../hooks/useApi'

const TABS = [
  { value: '', label: 'Tous les messages' },
  { value: 'integre', label: 'Intégrés' },
  { value: 'rejete', label: 'Rejetés' },
]

/** Résultat d'un message : la commande créée, ou les motifs de rejet. */
function Result({ message }: { message: EdiMessage }) {
  if (message.order) {
    return (
      <Link to={`/ventes/${message.order.id}`} onClick={(event) => event.stopPropagation()}>
        Commande {message.order.number}
      </Link>
    )
  }
  return (
    <ul className="errors">
      {message.errors.map((error) => (
        <li key={error}>{error}</li>
      ))}
    </ul>
  )
}

const COLUMNS: DataColumn<EdiMessage>[] = [
  {
    id: 'message',
    header: 'Message',
    sortValue: (m) => m.message_id,
    cell: (m) => <span className="lot-number">{m.message_id}</span>,
  },
  {
    id: 'customer',
    header: 'Enseigne',
    sortValue: (m) => m.customer_code,
    cell: (m) => m.customer_code ?? '—',
  },
  {
    id: 'received',
    header: 'Reçu le',
    sortValue: (m) => m.received_at,
    cell: (m) => formatDateTime(m.received_at),
  },
  {
    id: 'status',
    header: 'Statut',
    sortValue: (m) => m.status_label,
    cell: (m) => <StatusBadge status={m.status} label={m.status_label} />,
  },
  {
    id: 'result',
    header: 'Résultat',
    cell: (m) => (
      <span className="wrap">
        <Result message={m} />
      </span>
    ),
  },
]

/** Journal des messages EDI reçus des enseignes (simulés). */
export function EdiPage() {
  const { user } = useAuth()
  const [status, setStatus] = useState('')
  const [version, setVersion] = useState(0)
  const messages = useApi<Paginated<EdiMessage>>(
    `/api/ventes/edi-messages/?status=${status}&v=${version}`,
  )
  const [errors, setErrors] = useState<string[]>([])
  const [info, setInfo] = useState('')
  const [opened, setOpened] = useState<EdiMessage | null>(null)

  async function simulate() {
    setErrors([])
    setInfo('')
    try {
      const received = await apiPost<EdiMessage[]>('/api/ventes/edi-messages/simulate/')
      const rejected = received.filter((m) => m.status === 'rejete').length
      setInfo(`${received.length} message(s) reçu(s), dont ${rejected} rejeté(s).`)
      setVersion((v) => v + 1)
    } catch (error) {
      setErrors(errorMessages(error))
    }
  }

  return (
    <section>
      <div className="page-title">
        <h1>Messages EDI</h1>
        {hasRole(user, SALES_ROLES) && (
          <button type="button" onClick={() => void simulate()}>
            Simuler les commandes du jour
          </button>
        )}
      </div>
      <p className="page-intro">
        Chaque jour de semaine à 9 h 30, les enseignes « envoient » leurs commandes. Un message
        correct devient une commande client ; sinon il est rejeté avec le motif. Clique sur un
        message pour voir son contenu.
      </p>
      {info && (
        <p className="status status-ok" role="status">
          {info}
        </p>
      )}
      <ErrorList messages={errors} />
      <div className="tabs" role="tablist" aria-label="Statut des messages">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={status === tab.value}
            className={status === tab.value ? 'tab active' : 'tab'}
            onClick={() => setStatus(tab.value)}
          >
            {tab.label}
            {status === tab.value && messages.data && <span className="tab-count">{messages.data.count}</span>}
          </button>
        ))}
      </div>
      {messages.error && <p className="error">{messages.error}</p>}
      {messages.data && (
        <DataTable
          caption="Messages EDI"
          rows={messages.data.results}
          columns={COLUMNS}
          rowKey={(m) => m.id}
          onRowClick={setOpened}
          empty="Aucun message."
        />
      )}
      {opened && (
        <Drawer
          open
          onClose={() => setOpened(null)}
          title={`Message ${opened.message_id}`}
          subtitle={
            <>
              {opened.customer_code ?? 'Enseigne inconnue'} · reçu le {formatDateTime(opened.received_at)}{' '}
              <StatusBadge status={opened.status} label={opened.status_label} />
            </>
          }
          footer={
            opened.order && (
              <Link className="button secondary" to={`/ventes/${opened.order.id}`}>
                <ExternalLink size={15} aria-hidden="true" /> Commande {opened.order.number}
              </Link>
            )
          }
        >
          <h3>{opened.order ? 'Intégré' : 'Motifs du rejet'}</h3>
          {opened.order ? (
            <p>Ce message a créé la commande client {opened.order.number}.</p>
          ) : (
            <Result message={opened} />
          )}
          <h3>Contenu reçu</h3>
          <pre className="payload">{JSON.stringify(opened.payload, null, 2)}</pre>
        </Drawer>
      )}
    </section>
  )
}
