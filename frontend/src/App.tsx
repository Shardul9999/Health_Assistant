import { SignedIn, SignedOut, SignInButton, UserButton, useAuth } from '@clerk/clerk-react'
import { useEffect, useState } from 'react'
import DisclaimerBar from './components/DisclaimerBar'
import { apiFetch, fetchHealth, type HealthResponse } from './lib/api'

interface MeResponse {
  user_id: string
  session_id: string | null
  message: string
}

/**
 * Phase 1 shell. This screen exists to prove the foundations work end to end:
 * Clerk sign-in, a token that the backend actually verifies, and a live view of
 * the Postgres/Redis health check. Phase 3 replaces the body with the chat UI.
 */
function AuthedPanel() {
  const { getToken } = useAuth()
  const [me, setMe] = useState<MeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiFetch<MeResponse>('/api/me', getToken)
      .then(setMe)
      .catch((e: Error) => setError(e.message))
  }, [getToken])

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="mb-2 text-sm font-semibold text-slate-700">Backend token check</h2>
      {error && <p className="text-sm text-alert-700">{error}</p>}
      {!error && !me && <p className="text-sm text-slate-500">Verifying…</p>}
      {me && (
        <dl className="space-y-1 text-sm">
          <div className="flex gap-2">
            <dt className="w-28 shrink-0 text-slate-500">Clerk user</dt>
            <dd className="font-mono text-xs text-slate-800">{me.user_id}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-28 shrink-0 text-slate-500">Status</dt>
            <dd className="text-emerald-700">{me.message}</dd>
          </div>
        </dl>
      )}
    </div>
  )
}

function HealthPanel() {
  const [health, setHealth] = useState<HealthResponse | null>(null)

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => setHealth(null))
  }, [])

  const dot = (up: boolean | undefined) =>
    `inline-block h-2 w-2 rounded-full ${up ? 'bg-emerald-500' : 'bg-alert-600'}`

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="mb-2 text-sm font-semibold text-slate-700">Local infrastructure</h2>
      {!health ? (
        <p className="text-sm text-alert-700">Backend unreachable on {import.meta.env.VITE_API_BASE_URL}</p>
      ) : (
        <ul className="space-y-1 text-sm text-slate-700">
          <li>
            <span className={dot(health.database.reachable)} /> Postgres
            {health.database.pgvector && <span className="text-slate-500"> · pgvector enabled</span>}
          </li>
          <li>
            <span className={dot(health.redis.reachable)} /> Redis
          </li>
        </ul>
      )}
    </div>
  )
}

export default function App() {
  return (
    <div className="flex h-full flex-col bg-slate-50">
      <DisclaimerBar />

      <header className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
        <h1 className="text-base font-semibold text-slate-800">Health Symptom-Checker</h1>
        <SignedIn>
          <UserButton />
        </SignedIn>
        <SignedOut>
          <SignInButton mode="modal">
            <button className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700">
              Sign in
            </button>
          </SignInButton>
        </SignedOut>
      </header>

      <main className="mx-auto w-full max-w-2xl flex-1 space-y-4 overflow-y-auto p-4">
        <HealthPanel />
        <SignedIn>
          <AuthedPanel />
        </SignedIn>
        <SignedOut>
          <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">
            Sign in to verify the authenticated backend route.
          </div>
        </SignedOut>
      </main>
    </div>
  )
}
