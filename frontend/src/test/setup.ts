// Ajoute des vérifications pratiques comme toBeInTheDocument()
import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach } from 'vitest'

// Attente maximale d'un élément (findBy…) : 5 s au lieu de 1 s. Le premier affichage d'un
// fichier de tests dépasse parfois 1 s quand le PC est chargé (Docker, autres tests).
configure({ asyncUtilTimeout: 5000 })

// Vide la page entre deux tests
afterEach(() => {
  cleanup()
})
