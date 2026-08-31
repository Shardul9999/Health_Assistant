/**
 * Error banner for the codes in §4. RATE_LIMITED gets a live countdown, because
 * "try again later" without a number is the least useful thing to tell someone
 * mid-conversation.
 */

import { useEffect, useState } from 'react'
import type { ChatError } from '../types'

const COPY: Record<string, { title: string; tone: 'amber' | 'red' }> = {
  RATE_LIMITED: { title: 'Slow down a moment', tone: 'amber' },
  LLM_UNAVAILABLE: { title: 'Assistant unavailable', tone: 'red' },
  UNAUTHORIZED: { title: 'Session expired', tone: 'red' },
  NETWORK: { title: 'Connection problem', tone: 'red' },
  NOT_FOUND: { title: 'Conversation not found', tone: 'red' },
  UNKNOWN: { title: 'Something went wrong', tone: 'red' },
}

const TONES = {
  amber: 'border-amber-300 bg-amber-50 text-amber-900',
  red: 'border-alert-600/40 bg-alert-50 text-alert-700',
}

export default function RateLimitNotice({
  error,
  onDismiss,
}: {
  error: ChatError
  onDismiss: () => void
}) {
  const [remaining, setRemaining] = useState(error.retryAfterS ?? 0)

  useEffect(() => {
    setRemaining(error.retryAfterS ?? 0)
    if (!error.retryAfterS) return
    const timer = setInterval(() => {
      setRemaining((s) => {
        if (s <= 1) {
          clearInterval(timer)
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [error])

  const copy = COPY[error.code] ?? COPY.UNKNOWN

  return (
    <div role="status" className={`mx-auto my-2 flex max-w-2xl items-start gap-3 rounded-lg border px-4 py-3 text-sm ${TONES[copy.tone]}`}>
      <div className="flex-1">
        <p className="font-semibold">{copy.title}</p>
        <p className="mt-0.5 opacity-90">{error.message}</p>
        {error.code === 'RATE_LIMITED' && remaining > 0 && (
          <p className="mt-1.5 font-mono text-xs">
            You can send another message in {remaining}s
          </p>
        )}
        {error.code === 'RATE_LIMITED' && remaining === 0 && error.retryAfterS ? (
          <p className="mt-1.5 text-xs font-medium">You can send another message now.</p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss"
        className="shrink-0 rounded p-1 opacity-60 transition hover:bg-black/5 hover:opacity-100"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
          <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
        </svg>
      </button>
    </div>
  )
}
