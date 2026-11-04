/** Affiche les messages d'erreur renvoyés par le serveur (règles métier refusées…). */
export function ErrorList({ messages }: { messages: string[] }) {
  if (messages.length === 0) return null
  return (
    <div className="error-box" role="alert">
      <strong>L'opération a été refusée :</strong>
      <ul>
        {messages.map((message) => (
          <li key={message}>{message}</li>
        ))}
      </ul>
    </div>
  )
}
