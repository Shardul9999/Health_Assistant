/**
 * One message. Assistant messages carry their citation panel and a small
 * provenance footer (which model served it, how long it took) - useful in a demo
 * and the visible proof that the fallback in §7 actually switched.
 */

import type { ReactNode } from 'react'
import type { ChatMessage } from '../types'
import EmergencyBanner from './EmergencyBanner'
import SourceCitations from './SourceCitations'

/**
 * Minimal inline formatting. The model is asked for plain prose with **bold**,
 * bullets, and [Source Title] citations - not full markdown - so a parser would
 * be more machinery than the output warrants.
 */
function renderInline(text: string, keyPrefix: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|\[[^\]]+\])/g).map((part, i) => {
    const key = `${keyPrefix}-${i}`
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={key} className="font-semibold text-slate-900">
          {part.slice(2, -2)}
        </strong>
      )
    }
    if (part.startsWith('[') && part.endsWith(']')) {
      return (
        <span
          key={key}
          className="mx-0.5 rounded bg-brand-50 px-1 py-0.5 text-[11px] font-medium text-brand-700"
          title="Source this claim came from"
        >
          {part.slice(1, -1)}
        </span>
      )
    }
    return <span key={key}>{part}</span>
  })
}

function renderBody(content: string): ReactNode {
  const blocks: ReactNode[] = []
  let bullets: string[] = []

  const flushBullets = () => {
    if (bullets.length === 0) return
    blocks.push(
      <ul key={`ul-${blocks.length}`} className="my-2 ml-1 space-y-1.5">
        {bullets.map((b, i) => (
          <li key={i} className="flex gap-2">
            <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-slate-400" />
            <span>{renderInline(b, `li-${blocks.length}-${i}`)}</span>
          </li>
        ))}
      </ul>,
    )
    bullets = []
  }

  for (const rawLine of content.split('\n')) {
    const line = rawLine.trim()
    const bullet = line.match(/^[-*•]\s+(.*)$/)
    if (bullet) {
      bullets.push(bullet[1])
      continue
    }
    flushBullets()
    if (line) {
      blocks.push(
        <p key={`p-${blocks.length}`} className="my-1.5 first:mt-0 last:mb-0">
          {renderInline(line, `p-${blocks.length}`)}
        </p>,
      )
    }
  }
  flushBullets()
  return blocks
}

export default function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.redFlag) {
    return <EmergencyBanner content={message.content} category={message.redFlagCategory} />
  }

  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2.5 text-[15px] leading-relaxed text-white shadow-sm sm:max-w-[75%]">
          {message.content}
        </div>
      </div>
    )
  }

  const showCursor = message.pending && message.content.length > 0

  return (
    <div className="flex justify-start">
      <div className="w-full max-w-[92%] sm:max-w-[85%]">
        <div
          className={`rounded-2xl rounded-bl-sm border px-4 py-3 text-[15px] leading-relaxed shadow-sm ${
            message.noContext
              ? 'border-amber-200 bg-amber-50 text-amber-900'
              : 'border-slate-200 bg-white text-slate-800'
          }`}
        >
          {message.pending && message.content.length === 0 ? (
            <ThinkingDots />
          ) : (
            <>
              {renderBody(message.content)}
              {showCursor && (
                <span className="ml-0.5 inline-block h-4 w-[2px] animate-pulse bg-brand-600 align-middle" />
              )}
            </>
          )}
        </div>

        {!message.pending && (
          <>
            <SourceCitations sources={message.sources} />
            {(message.provider || message.latencyMs !== null) && (
              <p className="mt-1 px-2 text-[10px] text-slate-400">
                {message.provider && <>served by {message.provider}</>}
                {message.provider && message.latencyMs !== null && ' · '}
                {message.latencyMs !== null && <>{message.latencyMs} ms</>}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function ThinkingDots() {
  return (
    <span className="flex items-center gap-1 py-0.5" aria-label="Searching sources">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </span>
  )
}
