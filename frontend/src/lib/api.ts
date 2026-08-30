/**
 * Fetch wrapper that attaches the Clerk session token.
 *
 * Every call takes a `getToken` from Clerk's `useAuth()` rather than reading a
 * stored token: Clerk rotates short-lived session JWTs, and asking for one per
 * request is what keeps them fresh.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type GetToken = () => Promise<string | null>

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly retryAfterS?: number

  constructor(status: number, code: string, message: string, retryAfterS?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.retryAfterS = retryAfterS
  }
}

export async function apiFetch<T>(
  path: string,
  getToken: GetToken,
  init: RequestInit = {},
): Promise<T> {
  const token = await getToken()
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers })

  if (!res.ok) {
    // The backend returns {code, message} for every handled error; fall back to
    // the status text if something upstream returned a non-JSON body.
    const body = await res.json().catch(() => null)
    throw new ApiError(
      res.status,
      body?.code ?? 'UNKNOWN',
      body?.message ?? res.statusText,
      body?.retry_after_s,
    )
  }

  return res.json() as Promise<T>
}

/** Unauthenticated — used by the connection indicator. */
export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/health`)
  return res.json() as Promise<HealthResponse>
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  database: { reachable: boolean; pgvector?: boolean }
  redis: { reachable: boolean }
}
