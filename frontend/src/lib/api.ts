/**
 * Fetch wrapper that attaches the Clerk session token.
 *
 * Every call takes a `getToken` from Clerk's `useAuth()` rather than reading a
 * stored token: Clerk rotates short-lived session JWTs, and asking for one per
 * request is what keeps them fresh.
 */

import type { ChatSession, ErrorCode, StoredMessage } from '../types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type GetToken = () => Promise<string | null>

export class ApiError extends Error {
  readonly status: number
  readonly code: ErrorCode
  readonly retryAfterS?: number

  constructor(status: number, code: ErrorCode, message: string, retryAfterS?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.retryAfterS = retryAfterS
  }
}

async function authHeaders(getToken: GetToken, init: RequestInit = {}): Promise<Headers> {
  const token = await getToken()
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  return headers
}

async function toApiError(res: Response): Promise<ApiError> {
  // The backend returns {code, message} for every handled error; fall back to
  // the status text if something upstream returned a non-JSON body.
  const body = await res.json().catch(() => null)
  return new ApiError(
    res.status,
    body?.code ?? 'UNKNOWN',
    body?.message ?? res.statusText,
    body?.retry_after_s,
  )
}

export async function apiFetch<T>(
  path: string,
  getToken: GetToken,
  init: RequestInit = {},
): Promise<T> {
  const headers = await authHeaders(getToken, init)
  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers })
  if (!res.ok) throw await toApiError(res)
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

/** Opens the SSE stream. Returns the raw body for `readEventStream` to parse. */
export async function openChatStream(
  getToken: GetToken,
  body: { session_id: string | null; message: string },
  signal: AbortSignal,
): Promise<ReadableStream<Uint8Array>> {
  const headers = await authHeaders(getToken)
  headers.set('Accept', 'text/event-stream')

  const res = await fetch(`${BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal,
  })

  // A rate limit or auth failure arrives as a normal JSON error response, not as
  // an SSE frame, so it has to be handled before we start parsing the stream.
  if (!res.ok) throw await toApiError(res)
  if (!res.body) throw new ApiError(500, 'UNKNOWN', 'The server sent an empty response.')
  return res.body
}

// --------------------------------------------------------------------------- sessions

export const listSessions = (getToken: GetToken) =>
  apiFetch<ChatSession[]>('/api/sessions', getToken)

export const listMessages = (getToken: GetToken, sessionId: string) =>
  apiFetch<StoredMessage[]>(`/api/sessions/${sessionId}/messages`, getToken)

export const deleteSession = (getToken: GetToken, sessionId: string) =>
  apiFetch<void>(`/api/sessions/${sessionId}`, getToken, { method: 'DELETE' })

// --------------------------------------------------------------------------- health

export interface HealthResponse {
  status: 'ok' | 'degraded'
  database: { reachable: boolean; pgvector?: boolean }
  redis: { reachable: boolean }
}

/** Unauthenticated - used by the connection indicator. */
export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/health`)
  return res.json() as Promise<HealthResponse>
}
