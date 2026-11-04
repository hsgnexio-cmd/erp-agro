import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TEST_USER, mockApi, paginated, renderApp } from '../test/utils'

const LASAGNES = {
  id: 10,
  code: 'PF-PAT-LASBOL-BRE-300',
  name: 'Lasagnes bolognaise 300 g – Brévanne',
  article_type: 'PF',
  article_type_label: 'Produit fini',
  unit: 'u',
  category: null,
  category_code: null,
  recipe: 1,
  recipe_code: 'LASBOL',
  brand_customer: null,
  brand_code: 'BRE',
  format_size: 300,
  shelf_life_days: 14,
  date_type: 'DLC',
  storage_temperature_class: 'froid_positif',
  technical_sheet: '',
  specifications: '',
  allergens: [],
  allergen_names: [],
  has_bom: true,
  active: true,
}

const CREME = {
  ...LASAGNES,
  id: 20,
  code: 'MP-LAI-CREME35',
  name: 'Crème fraîche 35 % MG',
  article_type: 'MP',
  article_type_label: 'Matière première',
  unit: 'kg',
  recipe: null,
  recipe_code: null,
  brand_code: '',
  format_size: null,
  shelf_life_days: 21,
  allergen_names: ['Lait'],
  has_bom: false,
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Articles', () => {
  it('liste les articles avec leur durée de vie et leurs allergènes', async () => {
    mockApi({
      '/api/auth/me/': { body: TEST_USER },
      '/api/referentiel/articles/': { body: paginated([LASAGNES, CREME]) },
    })
    renderApp('/articles')

    expect(await screen.findByRole('link', { name: 'PF-PAT-LASBOL-BRE-300' })).toHaveAttribute(
      'href',
      '/articles/10',
    )
    expect(screen.getByText('MP-LAI-CREME35')).toBeInTheDocument()
    expect(screen.getByText('21 j (DLC)')).toBeInTheDocument()
    expect(screen.getByText('Lait')).toBeInTheDocument()
    expect(screen.getByText('2 article(s)')).toBeInTheDocument()
  })

  it("affiche la nomenclature d'un produit fini avec les quantités brutes", async () => {
    mockApi({
      '/api/auth/me/': { body: TEST_USER },
      '/api/referentiel/articles/10/': { body: LASAGNES },
      '/api/referentiel/boms/': {
        body: paginated([
          {
            id: 1,
            article: 10,
            article_code: LASAGNES.code,
            article_name: LASAGNES.name,
            article_unit: 'u',
            base_quantity: '1.000',
            comment: '',
            lines: [
              {
                id: 5,
                bom: 1,
                component: 30,
                component_code: 'MP-VIA-BOEUF15',
                component_name: 'Bœuf haché 15 % MG',
                component_type: 'MP',
                quantity: '0.1110',
                unit: 'kg',
                loss_rate: '25.00',
                gross_quantity: '0.1480',
              },
            ],
          },
        ]),
      },
    })
    renderApp('/articles/10')

    expect(await screen.findByRole('heading', { name: 'Nomenclature' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'MP-VIA-BOEUF15' })).toBeInTheDocument()
    expect(screen.getByText('25 %')).toBeInTheDocument()
    expect(screen.getByText('0,148')).toBeInTheDocument()
    expect(screen.getByText('Brévanne')).toBeInTheDocument()
  })
})
