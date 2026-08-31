/**
 * Collapsible citation panel.
 *
 * Collapsed by default so it does not bury the answer, but the count is always
 * visible: "5 sources" next to an answer is the signal that the thing is
 * grounded, and it is the first thing to open during a demo.
 */

import { useState } from 'react'
import type { SourceCitation } from '../types'

const ORG_STYLES: Record<string, string> = {
  WHO: 'bg-sky-100 text-sky-800',
  NHS: 'bg-indigo-100 text-indigo-800',
  CDC: 'bg-teal-100 text-teal-800',
}

function orgStyle(org: string): string {
  // NIH arrives as "NIH NHLBI", "NIH NIDDK", and so on.
  if (org.startsWith('NIH')) return 'bg-violet-100 text-violet-800'
  return ORG_STYLES[org] ?? 'bg-slate-100 text-slate-700'
}

export default function SourceCitations({ sources }: { sources: SourceCitation[] }) {
  const [open, setOpen] = useState(false)
  if (sources.length === 0) return null

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
      >
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
          className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-90' : ''}`}
        >
          <path
            fillRule="evenodd"
            d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
            clipRule="evenodd"
          />
        </svg>
        {sources.length} {sources.length === 1 ? 'source' : 'sources'}
      </button>

      {open && (
        <ul className="mt-2 space-y-2">
          {sources.map((s) => (
            <li
              key={s.id}
              className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 text-xs"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${orgStyle(s.source_org)}`}>
                  {s.source_org}
                </span>
                <a
                  href={s.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-brand-700 underline decoration-brand-300 underline-offset-2 hover:decoration-brand-600"
                >
                  {s.title}
                </a>
                <span
                  className="ml-auto shrink-0 font-mono text-[10px] text-slate-400"
                  title="Cosine similarity to your question"
                >
                  {s.similarity.toFixed(3)}
                </span>
              </div>
              <p className="mt-1.5 leading-relaxed text-slate-600">{s.snippet}</p>
              <p className="mt-1.5 text-[10px] text-slate-400">Licence: {s.license}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
