/** Message list, empty state, and composer. */

import { useEffect, useRef, useState } from 'react'
import type { ChatError, ChatMessage } from '../types'
import MessageBubble from './MessageBubble'
import RateLimitNotice from './RateLimitNotice'

const SUGGESTIONS = [
  'What causes iron deficiency anaemia?',
  'How is dengue spread, and how can I prevent it?',
  'What are the symptoms of typhoid?',
  'How can I tell a cold from the flu?',
]

interface Props {
  messages: ChatMessage[]
  isStreaming: boolean
  loadingHistory: boolean
  error: ChatError | null
  onSend: (text: string) => void
  onStop: () => void
  onDismissError: () => void
}

export default function ChatWindow({
  messages,
  isStreaming,
  loadingHistory,
  error,
  onSend,
  onStop,
  onDismissError,
}: Props) {
  const [draft, setDraft] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, error])

  // Grow the composer with its content, up to a ceiling.
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [draft])

  const submit = () => {
    const text = draft.trim()
    if (!text || isStreaming) return
    onSend(text)
    setDraft('')
  }

  const isEmpty = messages.length === 0 && !loadingHistory

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-3 py-4 sm:px-6">
          {loadingHistory && (
            <div className="space-y-3" aria-label="Loading conversation">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className={`h-16 animate-pulse rounded-2xl bg-slate-200/70 ${
                    i % 2 ? 'ml-auto w-2/3' : 'w-5/6'
                  }`}
                />
              ))}
            </div>
          )}

          {isEmpty && (
            <div className="flex flex-col items-center justify-center py-10 text-center sm:py-16">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600">
                <svg viewBox="0 0 24 24" fill="currentColor" className="h-6 w-6" aria-hidden="true">
                  <path d="M12 2a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0V8H8a1 1 0 010-2h3V3a1 1 0 011-1z" />
                  <path
                    fillRule="evenodd"
                    d="M4 13a1 1 0 011-1h14a1 1 0 011 1v6a3 3 0 01-3 3H7a3 3 0 01-3-3v-6zm3 2a1 1 0 100 2h10a1 1 0 100-2H7z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-slate-800">
                Ask about a health topic
              </h2>
              <p className="mt-1 max-w-md text-sm text-slate-500">
                Answers come only from verified references — WHO, NHS and NIH — and every claim
                is linked back to its source. If the library doesn&apos;t cover your question,
                you&apos;ll be told so rather than guessed at.
              </p>
              <div className="mt-6 grid w-full max-w-lg gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => onSend(s)}
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-left text-sm text-slate-700 shadow-sm transition hover:border-brand-300 hover:bg-brand-50/50 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-3">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
          </div>

          {error && <RateLimitNotice error={error} onDismiss={onDismissError} />}
          <div ref={endRef} />
        </div>
      </div>

      <div className="shrink-0 border-t border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto w-full max-w-3xl px-3 py-3 sm:px-6">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              submit()
            }}
            className="flex items-end gap-2"
          >
            <textarea
              ref={textareaRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                // Enter sends; Shift+Enter is a newline.
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  submit()
                }
              }}
              rows={1}
              maxLength={4000}
              placeholder="Ask a health question…"
              aria-label="Your question"
              className="min-h-[44px] flex-1 resize-none rounded-xl border border-slate-300 px-3.5 py-2.5 text-[15px] text-slate-800 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
            />
            {isStreaming ? (
              <button
                type="button"
                onClick={onStop}
                className="h-[44px] shrink-0 rounded-xl bg-slate-700 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
              >
                Stop
              </button>
            ) : (
              <button
                type="submit"
                disabled={!draft.trim()}
                aria-label="Send"
                className="flex h-[44px] w-[44px] shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1"
              >
                <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5" aria-hidden="true">
                  <path d="M3.105 2.29a.75.75 0 00-.826.95l1.414 4.926A1.5 1.5 0 005.135 9.25h6.115a.75.75 0 010 1.5H5.135a1.5 1.5 0 00-1.442 1.084l-1.414 4.926a.75.75 0 00.826.95 28.9 28.9 0 0015.293-7.155.75.75 0 000-1.109A28.9 28.9 0 003.105 2.29z" />
                </svg>
              </button>
            )}
          </form>
          <p className="mt-1.5 text-center text-[11px] text-slate-400">
            Enter to send · Shift+Enter for a new line
          </p>
        </div>
      </div>
    </div>
  )
}
