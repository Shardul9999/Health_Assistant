/** Mirrors the backend Pydantic schemas in app/schemas/chat.py. */

export interface SourceCitation {
  id: string
  title: string
  source_url: string
  source_org: string
  license: string
  snippet: string
  similarity: number
}

export interface ChatSession {
  id: string
  title: string | null
  created_at: string
}

export interface StoredMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  retrieved_chunk_ids: string[] | null
  llm_provider: string | null
  latency_ms: number | null
  was_red_flag: boolean
  created_at: string
}

/**
 * A message as the UI holds it. `pending` drives the streaming cursor;
 * `redFlagCategory` switches rendering from a chat bubble to EmergencyBanner.
 */
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources: SourceCitation[]
  provider: string | null
  latencyMs: number | null
  redFlag: boolean
  redFlagCategory: string | null
  noContext: boolean
  pending: boolean
  error: string | null
}

export type ErrorCode =
  | 'RATE_LIMITED'
  | 'UNAUTHORIZED'
  | 'LLM_UNAVAILABLE'
  | 'NOT_FOUND'
  | 'NETWORK'
  | 'UNKNOWN'

export interface ChatError {
  code: ErrorCode
  message: string
  retryAfterS?: number
}

/** The SSE events defined in plan §4, as a discriminated union. */
export type StreamEvent =
  | { type: 'session'; session_id: string }
  | { type: 'sources'; chunks: SourceCitation[] }
  | { type: 'token'; text: string }
  | { type: 'provider_switch'; provider: string }
  | { type: 'red_flag'; category: string; content: string }
  | { type: 'no_context'; content: string }
  | { type: 'done'; provider: string | null; latency_ms: number; red_flag: boolean }
  | { type: 'error'; code: ErrorCode; message: string; retry_after_s?: number }
