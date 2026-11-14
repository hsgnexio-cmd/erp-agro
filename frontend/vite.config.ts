import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Adresse du back-end Django. Dans Docker : http://backend:8000 (voir .env).
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // Les appels à /api sont redirigés vers Django : pas de problème de domaine croisé.
    proxy: {
      '/api': apiTarget,
    },
    // Sous Windows + Docker, il faut surveiller les fichiers par « polling ».
    watch: { usePolling: process.env.VITE_USE_POLLING === 'true' },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    // Les tests qui saisissent du texte sont lents sur une machine chargée (GitHub Actions)
    testTimeout: 15000,
  },
})
