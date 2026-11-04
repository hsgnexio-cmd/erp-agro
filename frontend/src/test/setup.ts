// Ajoute des vérifications pratiques comme toBeInTheDocument()
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Vide la page entre deux tests
afterEach(() => {
  cleanup()
})
