import { useEffect, useState } from 'react'

type ApiStatus = 'verification' | 'ok' | 'erreur'

const STATUS_LABELS: Record<ApiStatus, string> = {
  verification: 'Vérification de la connexion au serveur…',
  ok: 'Serveur et base de données connectés',
  erreur: 'Serveur injoignable',
}

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('verification')

  useEffect(() => {
    fetch('/api/health/')
      .then((response) => setApiStatus(response.ok ? 'ok' : 'erreur'))
      .catch(() => setApiStatus('erreur'))
  }, [])

  return (
    <main className="home">
      <h1>ERP Brévanne Traiteur</h1>
      <p className="subtitle">Plats cuisinés frais · Nantes · Rennes</p>
      <p className={`status status-${apiStatus}`} role="status">
        {STATUS_LABELS[apiStatus]}
      </p>
    </main>
  )
}

export default App
