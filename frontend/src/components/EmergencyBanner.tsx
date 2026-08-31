/**
 * Red-flag escalation UI (§6).
 *
 * Deliberately not a chat bubble. If an escalation looks like a normal reply it
 * reads as one more paragraph to skim, which is exactly the wrong response when
 * the content is "call an ambulance". Hence the full-width card, the alert
 * colour, the icon, and the phone numbers rendered as tap-to-call buttons rather
 * than as digits inside a sentence.
 */

import type { ReactNode } from 'react'

const EMERGENCY = { label: 'Emergency', number: '112' }
const AMBULANCE = { label: 'Ambulance', number: '108' }
const TELE_MANAS = { label: 'Tele-MANAS', number: '14416' }

/** Bold the **segments** in the fixed escalation text from the backend. */
function renderText(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? (
      <strong key={i} className="font-semibold">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  )
}

function CallButton({ label, number }: { label: string; number: string }) {
  return (
    <a
      href={`tel:${number}`}
      className="inline-flex items-center gap-2 rounded-lg bg-alert-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-alert-700 focus:outline-none focus:ring-2 focus:ring-alert-600 focus:ring-offset-2"
    >
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
        <path d="M2 3a1 1 0 011-1h2.2a1 1 0 01.97.757l.83 3.32a1 1 0 01-.53 1.13l-1.5.75a11.5 11.5 0 005.07 5.07l.75-1.5a1 1 0 011.13-.53l3.32.83A1 1 0 0118 12.8V15a1 1 0 01-1 1h-1C8.16 16 2 9.84 2 2V3z" />
      </svg>
      {label} {number}
    </a>
  )
}

export default function EmergencyBanner({
  content,
  category,
}: {
  content: string
  category: string | null
}) {
  const isMentalHealth = category === 'self_harm'
  const paragraphs = content.split('\n\n').filter(Boolean)

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="my-3 overflow-hidden rounded-xl border-2 border-alert-600 bg-alert-50 shadow-sm"
    >
      <div className="flex items-center gap-2 bg-alert-600 px-4 py-2 text-white">
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5 shrink-0" aria-hidden="true">
          <path
            fillRule="evenodd"
            d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 8a1 1 0 100-2 1 1 0 000 2z"
            clipRule="evenodd"
          />
        </svg>
        <span className="text-sm font-bold uppercase tracking-wide">
          {isMentalHealth ? 'Please reach out for support' : 'Seek emergency care now'}
        </span>
      </div>

      <div className="space-y-3 px-4 py-4 text-[15px] leading-relaxed text-alert-900">
        {paragraphs.map((p, i) => (
          <p key={i}>{renderText(p)}</p>
        ))}

        <div className="flex flex-wrap gap-2 pt-1">
          {isMentalHealth ? (
            <>
              <CallButton {...TELE_MANAS} />
              <CallButton {...EMERGENCY} />
            </>
          ) : (
            <>
              <CallButton {...EMERGENCY} />
              <CallButton {...AMBULANCE} />
            </>
          )}
        </div>

        <p className="pt-1 text-xs text-alert-700">
          This assistant did not analyse your symptoms and cannot tell you what is causing them.
        </p>
      </div>
    </div>
  )
}
