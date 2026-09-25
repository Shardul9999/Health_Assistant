import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react'
import { useCallback, useState } from 'react'
import ChatWindow from './components/ChatWindow'
import DisclaimerBar from './components/DisclaimerBar'
import SessionSidebar from './components/SessionSidebar'
import { useChat } from './hooks/useChat'
import { useSessions } from './hooks/useSessions'

function Chat() {
  const { sessions, activeId, setActiveId, adoptSession, startNew, remove, loading } = useSessions()
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 1024
    }
    return true
  })

  const onSessionCreated = useCallback((id: string) => adoptSession(id), [adoptSession])
  const { messages, send, stop, isStreaming, loadingHistory, error, clearError } = useChat(
    activeId,
    onSessionCreated,
  )

  return (
    <div className="flex min-h-0 flex-1">
      <SessionSidebar
        sessions={sessions}
        activeId={activeId}
        loading={loading}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onSelect={setActiveId}
        onNew={startNew}
        onDelete={remove}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex shrink-0 items-center gap-2 border-b border-slate-200 bg-white px-3 py-2.5 sm:px-6">
          <button
            type="button"
            onClick={() => setSidebarOpen((prev) => !prev)}
            aria-label={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
            title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
            className="rounded-lg p-2 text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-5 w-5"
              aria-hidden="true"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="9" y1="3" x2="9" y2="21" />
            </svg>
          </button>
          <h1 className="min-w-0 flex-1 truncate text-sm font-semibold text-slate-800 sm:text-base">
            Health Symptom-Checker
          </h1>
          <UserButton afterSignOutUrl="/" />
        </header>

        <ChatWindow
          messages={messages}
          isStreaming={isStreaming}
          loadingHistory={loadingHistory}
          error={error}
          onSend={send}
          onStop={stop}
          onDismissError={clearError}
        />
      </div>
    </div>
  )
}

function SignedOutLanding() {
  return (
    <div className="flex flex-1 items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600">
          <svg viewBox="0 0 24 24" fill="currentColor" className="h-6 w-6" aria-hidden="true">
            <path d="M11 3a1 1 0 112 0v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0V8H8a1 1 0 010-2h3V3z" />
            <path
              fillRule="evenodd"
              d="M4 13a1 1 0 011-1h14a1 1 0 011 1v5a3 3 0 01-3 3H7a3 3 0 01-3-3v-5z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <h1 className="text-xl font-semibold text-slate-800">Health Symptom-Checker</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          A grounded assistant that answers health questions only from verified references —
          WHO, NHS and NIH — and links every claim back to its source.
        </p>
        <SignInButton mode="modal">
          <button className="mt-6 w-full rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2">
            Sign in to continue
          </button>
        </SignInButton>
        <p className="mt-4 text-xs text-slate-400">
          Informational only. Not a substitute for professional medical advice.
        </p>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <div className="flex h-full flex-col bg-slate-50">
      <DisclaimerBar />
      <SignedIn>
        <Chat />
      </SignedIn>
      <SignedOut>
        <SignedOutLanding />
      </SignedOut>
    </div>
  )
}
