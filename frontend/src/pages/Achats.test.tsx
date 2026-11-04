import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PurchaseOrder, Reception } from '../api/types'
import { TEST_USER, mockApi, paginated, renderApp } from '../test/utils'

const BUYER = { ...TEST_USER, roles: ['acheteur'] }
const STOREKEEPER = { ...TEST_USER, roles: ['magasinier'] }

const ORDER: PurchaseOrder = {
  id: 7,
  number: 'CA-2026-00007',
  supplier: 4,
  supplier_code: 'FOU-004',
  supplier_name: 'Crèmerie Bretonne',
  delivery_site: 1,
  delivery_site_code: 'MPE',
  order_date: '2026-11-01',
  expected_delivery_date: '2026-11-04',
  status: 'envoyee',
  status_label: 'Envoyée',
  comment: '',
  created_by_name: 'paul',
  created_at: '2026-11-01T08:00:00Z',
  sent_at: '2026-11-01T08:05:00Z',
  total_amount: '420.00',
  lines: [
    {
      id: 70,
      article: 20,
      article_code: 'MP-LAI-CREME35',
      article_name: 'Crème fraîche 35 % MG',
      article_date_type: 'DLC',
      article_temperature_class: 'froid_positif',
      quantity: '100.000',
      unit: 'kg',
      unit_price: '4.2000',
      amount: '420.00',
      received_quantity: '0.000',
    },
  ],
  reception_ids: [],
}

const BLOCKED_RECEPTION: Reception = {
  id: 3,
  number: 'REC-2026-00003',
  order: 7,
  order_number: ORDER.number,
  supplier_name: ORDER.supplier_name,
  received_at: '2026-11-04T07:30:00Z',
  received_by_name: 'marc',
  delivery_note_number: 'BL-118',
  documents_ok: true,
  location: 5,
  location_code: 'MPE-QUAR',
  comment: '',
  is_compliant: false,
  lines: [
    {
      id: 30,
      order_line: 70,
      article_code: 'MP-LAI-CREME35',
      article_name: 'Crème fraîche 35 % MG',
      unit: 'kg',
      quantity: '100.000',
      supplier_lot_number: 'CB-0412',
      expiry_date: '2026-11-24',
      temperature: '6.5',
      appearance_ok: true,
      is_compliant: false,
      non_compliance_reasons: 'Température de 6,5 °C au-dessus du maximum de 4 °C',
      lot: 9,
      lot_number: 'LR-261104-0001',
      lot_status: 'bloque',
    },
  ],
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Commandes fournisseurs', () => {
  it("crée une commande à partir du catalogue du fournisseur", async () => {
    const fetchMock = mockApi({
      '/api/auth/me/': { body: BUYER },
      '/api/referentiel/suppliers/': {
        body: paginated([{ id: 4, code: 'FOU-004', name: 'Crèmerie Bretonne' }]),
      },
      '/api/referentiel/sites/': { body: paginated([{ id: 1, code: 'MPE', name: 'Entrepôt' }]) },
      '/api/achats/catalog/': {
        body: [
          {
            article: 20,
            article_code: 'MP-LAI-CREME35',
            article_name: 'Crème fraîche 35 % MG',
            unit: 'kg',
            min_order_quantity: null,
            unit_price: '4.2000',
          },
        ],
      },
      '/api/achats/orders/': { status: 201, body: { ...ORDER, status: 'brouillon' } },
    })
    renderApp('/commandes/nouvelle')
    const user = userEvent.setup()

    await user.selectOptions(
      await screen.findByLabelText('Fournisseur'),
      await screen.findByRole('option', { name: 'FOU-004 – Crèmerie Bretonne' }),
    )
    await user.type(await screen.findByLabelText('Quantité MP-LAI-CREME35'), '100')
    expect(screen.getByText(/1 ligne\(s\)/)).toHaveTextContent('420,00')
    await user.click(screen.getByRole('button', { name: 'Enregistrer en brouillon' }))

    const call = fetchMock.mock.calls.find(
      ([url, init]) => url === '/api/achats/orders/' && init?.method === 'POST',
    )
    expect(JSON.parse(call?.[1]?.body as string)).toMatchObject({
      supplier: 4,
      delivery_site: 1,
      lines: [{ article: 20, quantity: '100' }],
    })
  })

  it("montre les boutons selon le rôle : l'acheteur envoie, le magasinier réceptionne", async () => {
    mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/achats/orders/7/': { body: ORDER },
      '/api/achats/receptions/': { body: paginated([]) },
    })
    renderApp('/commandes/7')

    expect(await screen.findByRole('link', { name: 'Réceptionner' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Annuler la commande' })).not.toBeInTheDocument()
  })

  it('affiche clairement les erreurs renvoyées par le serveur', async () => {
    mockApi({
      '/api/auth/me/': { body: BUYER },
      '/api/achats/orders/7/send/': {
        status: 400,
        body: { non_field_errors: ['Seule une commande en brouillon peut être envoyée.'] },
      },
      '/api/achats/orders/7/': { body: { ...ORDER, status: 'brouillon', status_label: 'Brouillon' } },
      '/api/achats/receptions/': { body: paginated([]) },
    })
    renderApp('/commandes/7')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Envoyer au fournisseur' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Seule une commande en brouillon peut être envoyée.',
    )
  })
})

describe('Réception', () => {
  it('enregistre une réception et montre le lot bloqué avec son motif', async () => {
    const fetchMock = mockApi({
      '/api/auth/me/': { body: STOREKEEPER },
      '/api/achats/orders/7/': { body: ORDER },
      '/api/referentiel/locations/': {
        body: paginated([{ id: 5, code: 'MPE-QUAR', name: 'Quarantaine' }]),
      },
      '/api/achats/receptions/': { status: 201, body: BLOCKED_RECEPTION },
    })
    renderApp('/commandes/7/reception')
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText('N° de bon de livraison'), 'BL-118')
    await screen.findByRole('option', { name: 'MPE-QUAR – Quarantaine' })
    const line = screen.getByRole('group', { name: /MP-LAI-CREME35/ })
    await user.type(within(line).getByLabelText('Lot fournisseur'), 'CB-0412')
    await user.type(within(line).getByLabelText('DLC'), '2026-11-24')
    await user.type(within(line).getByLabelText('Température (°C)'), '6.5')
    await user.click(screen.getByRole('button', { name: 'Enregistrer la réception' }))

    expect(await screen.findByText('⚠️ Réception non conforme')).toBeInTheDocument()
    expect(screen.getByText('Bloqué')).toBeInTheDocument()
    expect(screen.getByText(/6,5 °C au-dessus du maximum/)).toBeInTheDocument()

    const call = fetchMock.mock.calls.find(([url]) => url === '/api/achats/receptions/')
    expect(JSON.parse(call?.[1]?.body as string)).toEqual({
      order: 7,
      location: 5,
      delivery_note_number: 'BL-118',
      documents_ok: true,
      lines: [
        {
          order_line: 70,
          quantity: '100',
          supplier_lot_number: 'CB-0412',
          expiry_date: '2026-11-24',
          temperature: '6.5',
          appearance_ok: true,
        },
      ],
    })
  })
})

describe('Lots', () => {
  it('liste les lots avec leur statut et le motif de blocage', async () => {
    mockApi({
      '/api/auth/me/': { body: TEST_USER },
      '/api/stocks/lots/': {
        body: paginated([
          {
            id: 9,
            number: 'LR-261104-0001',
            article: 20,
            article_code: 'MP-LAI-CREME35',
            article_name: 'Crème fraîche 35 % MG',
            article_type: 'MP',
            unit: 'kg',
            supplier_code: 'FOU-004',
            supplier_lot_number: 'CB-0412',
            reception_date: '2026-11-04',
            date_type: 'DLC',
            expiry_date: '2026-11-24',
            initial_quantity: '100.000',
            quantity: '100.000',
            location_code: 'MPE-QUAR',
            site_code: 'MPE',
            status: 'bloque',
            status_label: 'Bloqué',
            block_reason: 'Température de 6,5 °C au-dessus du maximum de 4 °C',
            reception_number: 'REC-2026-00003',
            created_at: '2026-11-04T07:30:00Z',
          },
        ]),
      },
    })
    renderApp('/lots')

    expect(await screen.findByText('LR-261104-0001')).toBeInTheDocument()
    expect(screen.getByText('100 kg')).toBeInTheDocument()
    expect(screen.getByText('24/11/2026 (DLC)')).toBeInTheDocument()
    expect(screen.getByText(/6,5 °C au-dessus/)).toBeInTheDocument()
  })
})
