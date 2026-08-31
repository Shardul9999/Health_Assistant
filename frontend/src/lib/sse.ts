/**
 * Server-Sent Events parsing.
 *
 * We use `fetch` + `ReadableStream` rather than `EventSource` because the chat
 * endpoint requires an `Authorization` header and EventSource cannot send one.
 *
 * The parsing is split out as a pure function because the hard part is not the
 * format, it is that network chunks land on arbitrary byte boundaries: a single
 * `data:` line can arrive in three pieces, and a chunk can end halfway through a
 * multi-byte UTF-8 character. Both are exercised in sse.test.ts.
 */

import type { StreamEvent } from '../types'

/**
 * Consume as many complete events as `buffer` holds.
 * Returns the parsed events plus whatever trailing partial text must be kept.
 */
export function drainBuffer(buffer: string): { events: StreamEvent[]; rest: string } {
  const events: StreamEvent[] = []

  // Events are separated by a blank line. Normalise CRLF first - the spec allows
  // either, and a proxy may rewrite them.
  const normalised = buffer.replace(/\r\n/g, '\n')
  const parts = normalised.split('\n\n')

  // The final part is whatever came after the last blank line: either an
  // incomplete event, or an empty string. Either way it stays in the buffer.
  const rest = parts.pop() ?? ''

  for (const block of parts) {
    const event = parseBlock(block)
    if (event) events.push(event)
  }

  return { events, rest }
}

function parseBlock(block: string): StreamEvent | null {
  let name = 'message'
  const dataLines: string[] = []

  for (const line of block.split('\n')) {
    if (!line || line.startsWith(':')) continue // blank or comment/heartbeat
    const colon = line.indexOf(':')
    const field = colon === -1 ? line : line.slice(0, colon)
    // "field: value" - exactly one leading space is part of the framing.
    let value = colon === -1 ? '' : line.slice(colon + 1)
    if (value.startsWith(' ')) value = value.slice(1)

    if (field === 'event') name = value
    else if (field === 'data') dataLines.push(value)
  }

  if (dataLines.length === 0) return null

  // Multi-line data fields are joined with newlines, per the SSE spec.
  const raw = dataLines.join('\n')
  let payload: Record<string, unknown>
  try {
    payload = JSON.parse(raw)
  } catch {
    // A malformed frame must not kill the stream - the rest of the answer is
    // still worth showing.
    return null
  }

  return { type: name, ...payload } as StreamEvent
}

/** Async-iterate the parsed events of a streaming response body. */
export async function* readEventStream(
  body: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const reader = body.getReader()
  // `stream: true` is what makes a multi-byte character split across two chunks
  // decode correctly instead of turning into a replacement character.
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      if (signal?.aborted) return
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const { events, rest } = drainBuffer(buffer)
      buffer = rest
      for (const event of events) yield event
    }

    // Flush anything the server sent without a trailing blank line.
    buffer += decoder.decode()
    if (buffer.trim()) {
      const { events } = drainBuffer(buffer + '\n\n')
      for (const event of events) yield event
    }
  } finally {
    reader.releaseLock()
  }
}
