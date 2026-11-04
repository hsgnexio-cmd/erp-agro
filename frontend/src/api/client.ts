// Appels à l'API Django. Les cookies de session sont envoyés automatiquement.

export class ApiError extends Error {
  status: number
  /** Corps de la réponse d'erreur (ex. { lines: ["MP-LAI-CREME35 : …"] }) */
  details: unknown

  constructor(status: number, message: string, details: unknown = null) {
    super(message)
    this.status = status
    this.details = details
  }
}

function getCookie(name: string): string | null {
  const match = document.cookie.split('; ').find((row) => row.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.split('=')[1]) : null
}

/** Rassemble tous les messages d'une erreur de l'API en une liste lisible. */
export function errorMessages(error: unknown): string[] {
  if (!(error instanceof ApiError)) {
    return [error instanceof Error ? error.message : 'Erreur inattendue.']
  }
  const messages: string[] = []
  const collect = (value: unknown) => {
    if (typeof value === 'string') messages.push(value)
    else if (Array.isArray(value)) value.forEach(collect)
    else if (value && typeof value === 'object') Object.values(value).forEach(collect)
  }
  collect(error.details)
  return messages.length > 0 ? messages : [error.message]
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (method !== 'GET') {
    headers.set('Content-Type', 'application/json')
    // Jeton de sécurité exigé par Django pour toute modification
    const csrfToken = getCookie('csrftoken')
    if (csrfToken) headers.set('X-CSRFToken', csrfToken)
  }

  const response = await fetch(path, { ...options, headers, credentials: 'same-origin' })
  if (!response.ok) {
    let message =
      response.status === 403
        ? 'Accès refusé par le serveur (erreur 403).'
        : `Erreur du serveur (${response.status}).`
    let details: unknown = null
    try {
      details = await response.json()
      const detail = (details as { detail?: unknown }).detail
      if (typeof detail === 'string') message = detail
    } catch {
      // réponse sans JSON : on garde le message par défaut
    }
    throw new ApiError(response.status, message, details)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const apiGet = <T>(path: string) => apiRequest<T>(path)

export const apiPost = <T>(path: string, body?: unknown) =>
  apiRequest<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
