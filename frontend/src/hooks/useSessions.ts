import { useAuth } from '@clerk/clerk-react'
import { useCallback, useEffect, useState } from 'react'
import { deleteSession as deleteSessionApi, listSessions } from '../lib/api'
import type { ChatSession } from '../types'

export function useSessions() {
  const { getToken, isSignedIn } = useAuth()
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    if (!isSignedIn) return
    setLoading(true)
    try {
      setSessions(await listSessions(getToken))
    } catch {
      // The sidebar is not worth an error banner - the chat itself will report
      // any real connectivity problem.
    } finally {
      setLoading(false)
    }
  }, [getToken, isSignedIn])

  useEffect(() => {
    void refresh()
  }, [refresh])

  /** Called when the backend reports the session id for a brand-new chat. */
  const adoptSession = useCallback(
    (id: string) => {
      setActiveId((current) => {
        if (current === id) return current
        void refresh()
        return id
      })
    },
    [refresh],
  )

  const startNew = useCallback(() => setActiveId(null), [])

  const remove = useCallback(
    async (id: string) => {
      // Optimistic: the row disappears immediately, and refresh() reconciles.
      setSessions((prev) => prev.filter((s) => s.id !== id))
      setActiveId((current) => (current === id ? null : current))
      try {
        await deleteSessionApi(getToken, id)
      } finally {
        void refresh()
      }
    },
    [getToken, refresh],
  )

  return { sessions, activeId, setActiveId, adoptSession, startNew, remove, loading, refresh }
}
