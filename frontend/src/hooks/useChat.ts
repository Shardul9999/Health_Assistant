import { useAuth } from '@clerk/clerk-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, listMessages, openChatStream } from '../lib/api'
import { readEventStream } from '../lib/sse'
import type { ChatError, ChatMessage, SourceCitation, StoredMessage } from '../types'

const newId = () =>
  globalThis.crypto?.randomUUID?.() ?? `tmp-${Date.now()}-${Math.random().toString(36).slice(2)}`

function emptyAssistant(): ChatMessage {
  return {
    id: newId(),
    role: 'assistant',
    content: '',
    sources: [],
    provider: null,
    latencyMs: null,
    redFlag: false,
    redFlagCategory: null,
    noContext: false,
    pending: true,
    error: null,
  }
}

function fromStored(m: StoredMessage): ChatMessage {
  return {
    id: m.id,
    role: m.role,
    content: m.content,
    sources: [], // chunk ids are stored, but the citation payload is not replayed
    provider: m.llm_provider,
    latencyMs: m.latency_ms,
    redFlag: m.was_red_flag,
    redFlagCategory: null,
    noContext: false,
    pending: false,
    error: null,
  }
}

export function useChat(sessionId: string | null, onSessionCreated: (id: string) => void) {
  const { getToken } = useAuth()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<ChatError | null>(null)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  // The session this hook is currently streaming into. A brand-new chat starts
  // with sessionId === null and learns its id from the stream's first event,
  // which then flows back down as a prop change. Without this guard the history
  // effect below reads that as the user switching conversations and aborts the
  // very stream that produced the id.
  const streamingSessionRef = useRef<string | null>(null)

  /** Replace the trailing assistant message, which is the one being streamed. */
  const patchLast = useCallback((patch: Partial<ChatMessage>) => {
    setMessages((prev) => {
      if (prev.length === 0) return prev
      const next = [...prev]
      next[next.length - 1] = { ...next[next.length - 1], ...patch }
      return next
    })
  }, [])

  // Load history when the user switches sessions.
  useEffect(() => {
    // Not a switch: this is the id our own in-flight stream just announced.
    // Leave the stream and the messages already on screen alone.
    if (sessionId && sessionId === streamingSessionRef.current) return

    abortRef.current?.abort()
    setError(null)

    if (!sessionId) {
      setMessages([])
      return
    }

    let cancelled = false
    setLoadingHistory(true)
    listMessages(getToken, sessionId)
      .then((stored) => {
        if (!cancelled) setMessages(stored.map(fromStored))
      })
      .catch((e: unknown) => {
        if (cancelled) return
        const err = e as ApiError
        setError({ code: err.code ?? 'UNKNOWN', message: err.message })
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false)
      })

    return () => {
      cancelled = true
    }
  }, [sessionId, getToken])

  const stop = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setIsStreaming(false)
    patchLast({ pending: false })
  }, [patchLast])

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || isStreaming) return

      setError(null)
      const controller = new AbortController()
      abortRef.current = controller

      setMessages((prev) => [
        ...prev,
        { ...emptyAssistant(), id: newId(), role: 'user', content: trimmed, pending: false },
        emptyAssistant(),
      ])
      setIsStreaming(true)

      try {
        const body = await openChatStream(
          getToken,
          { session_id: sessionId, message: trimmed },
          controller.signal,
        )

        let streamed = ''
        let sources: SourceCitation[] = []

        for await (const event of readEventStream(body, controller.signal)) {
          switch (event.type) {
            case 'session':
              streamingSessionRef.current = event.session_id
              onSessionCreated(event.session_id)
              break

            case 'sources':
              sources = event.chunks
              patchLast({ sources })
              break

            case 'token':
              streamed += event.text
              patchLast({ content: streamed })
              break

            case 'provider_switch':
              // §7: the primary died mid-answer. Throw away what we have shown
              // rather than splicing two half-answers together.
              streamed = ''
              patchLast({ content: '', provider: event.provider })
              break

            case 'red_flag':
              patchLast({
                content: event.content,
                redFlag: true,
                redFlagCategory: event.category,
                sources: [],
                pending: false,
              })
              break

            case 'no_context':
              patchLast({ content: event.content, noContext: true, pending: false })
              break

            case 'done':
              patchLast({
                provider: event.provider,
                latencyMs: event.latency_ms,
                pending: false,
              })
              break

            case 'error':
              setError({
                code: event.code,
                message: event.message,
                retryAfterS: event.retry_after_s,
              })
              // Drop the empty assistant placeholder; the banner carries the news.
              setMessages((prev) => prev.slice(0, -1))
              break
          }
        }
      } catch (e: unknown) {
        if (controller.signal.aborted) return
        const err = e as ApiError
        const code = err instanceof ApiError ? err.code : 'NETWORK'
        setError({
          code,
          message:
            code === 'NETWORK'
              ? "Couldn't reach the assistant. Check that the backend is running."
              : err.message,
          retryAfterS: err.retryAfterS,
        })
        setMessages((prev) => prev.slice(0, -1))
      } finally {
        setIsStreaming(false)
        abortRef.current = null
        streamingSessionRef.current = null
        patchLast({ pending: false })
      }
    },
    [getToken, isStreaming, onSessionCreated, patchLast, sessionId],
  )

  // Abort an in-flight stream if the component goes away mid-answer.
  useEffect(() => () => abortRef.current?.abort(), [])

  return { messages, send, stop, isStreaming, loadingHistory, error, clearError: () => setError(null) }
}
