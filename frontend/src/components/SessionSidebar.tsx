/**
 * Conversation list. A drawer on mobile, a fixed column from `sm` up.
 */

import type { ChatSession } from '../types'

interface Props {
  sessions: ChatSession[]
  activeId: string | null
  loading: boolean
  open: boolean
  onClose: () => void
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
}

function formatDate(iso: string): string {
  const date = new Date(iso)
  const today = new Date()
  const isToday = date.toDateString() === today.toDateString()
  return isToday
    ? date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    : date.toLocaleDateString([], { day: 'numeric', month: 'short' })
}

export default function SessionSidebar({
  sessions,
  activeId,
  loading,
  open,
  onClose,
  onSelect,
  onNew,
  onDelete,
}: Props) {
  const handleSelect = (id: string) => {
    onSelect(id)
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      onClose()
    }
  }

  const handleNew = () => {
    onNew()
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      onClose()
    }
  }

  return (
    <>
      {/* Scrim: mobile/tablet overlay when open */}
      {open && (
        <div
          className="fixed inset-0 z-20 bg-slate-900/40 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-30 flex flex-col border-r border-slate-200 bg-white transition-all duration-200 lg:static lg:z-auto ${
          open
            ? 'w-72 translate-x-0 lg:w-64'
            : '-translate-x-full w-72 lg:w-0 lg:translate-x-0 lg:overflow-hidden lg:border-r-0'
        }`}
        aria-label="Conversations"
      >
        <div className="border-b border-slate-200 p-3">
          <button
            type="button"
            onClick={handleNew}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
              <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
            </svg>
            New chat
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto p-2">
          {loading && sessions.length === 0 && (
            <div className="space-y-2 p-1">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-9 animate-pulse rounded-lg bg-slate-100" />
              ))}
            </div>
          )}

          {!loading && sessions.length === 0 && (
            <p className="px-3 py-6 text-center text-xs text-slate-400">
              No conversations yet. Ask a question to start one.
            </p>
          )}

          <ul className="space-y-0.5">
            {sessions.map((session) => {
              const isActive = session.id === activeId
              return (
                <li key={session.id} className="group relative">
                  <button
                    type="button"
                    onClick={() => handleSelect(session.id)}
                    className={`w-full truncate rounded-lg py-2 pl-3 pr-8 text-left text-sm transition ${
                      isActive
                        ? 'bg-brand-50 font-medium text-brand-800'
                        : 'text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <span className="block truncate">{session.title || 'Untitled'}</span>
                    <span className="block text-[10px] text-slate-400">
                      {formatDate(session.created_at)}
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(session.id)}
                    aria-label={`Delete conversation: ${session.title || 'Untitled'}`}
                    className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-1.5 text-slate-400 opacity-0 transition hover:bg-alert-50 hover:text-alert-600 focus:opacity-100 group-hover:opacity-100"
                  >
                    <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5" aria-hidden="true">
                      <path
                        fillRule="evenodd"
                        d="M8.75 1a1 1 0 00-.95.69L7.56 2.5H4.25a.75.75 0 000 1.5h11.5a.75.75 0 000-1.5h-3.31l-.24-.81A1 1 0 0011.25 1h-2.5zM5.06 5.5l.62 10.05A1.5 1.5 0 007.18 17h5.64a1.5 1.5 0 001.5-1.45l.62-10.05H5.06z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>
      </aside>
    </>
  )
}
