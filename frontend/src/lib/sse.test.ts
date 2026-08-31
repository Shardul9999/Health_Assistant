/**
 * SSE parsing (plan §10: "Vitest for useChat stream parsing").
 *
 * The format itself is trivial. What these tests are really about is chunk
 * boundaries: the network splits the byte stream wherever it likes, and a naive
 * parser that assumes one chunk equals one event drops tokens silently - which
 * would show up as an answer with words missing rather than as a crash.
 */

import { describe, expect, it } from 'vitest'
import { drainBuffer, readEventStream } from './sse'

const frame = (event: string, data: unknown) =>
  `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`

/** Feeds `text` through a ReadableStream cut into pieces of `size` bytes. */
function streamOf(text: string, size = Infinity): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(text)
  let offset = 0
  return new ReadableStream({
    pull(controller) {
      if (offset >= bytes.length) {
        controller.close()
        return
      }
      const end = Math.min(offset + size, bytes.length)
      controller.enqueue(bytes.slice(offset, end))
      offset = end
    },
  })
}

async function collect(text: string, chunkSize?: number) {
  const events = []
  for await (const e of readEventStream(streamOf(text, chunkSize))) events.push(e)
  return events
}

// --------------------------------------------------------------------------- drainBuffer

describe('drainBuffer', () => {
  it('parses a complete event', () => {
    const { events, rest } = drainBuffer(frame('token', { text: 'Hello' }))
    expect(events).toEqual([{ type: 'token', text: 'Hello' }])
    expect(rest).toBe('')
  })

  it('keeps an incomplete trailing event in the buffer', () => {
    const { events, rest } = drainBuffer(
      frame('token', { text: 'A' }) + 'event: token\ndata: {"text":"B"',
    )
    expect(events).toHaveLength(1)
    expect(rest).toBe('event: token\ndata: {"text":"B"')
  })

  it('parses several events from one buffer', () => {
    const buffer = frame('token', { text: 'a' }) + frame('token', { text: 'b' })
    expect(drainBuffer(buffer).events).toHaveLength(2)
  })

  it('tolerates CRLF line endings', () => {
    const { events } = drainBuffer('event: token\r\ndata: {"text":"hi"}\r\n\r\n')
    expect(events).toEqual([{ type: 'token', text: 'hi' }])
  })

  it('ignores comment lines used as heartbeats', () => {
    const { events } = drainBuffer(': keep-alive\n\n' + frame('token', { text: 'x' }))
    expect(events).toEqual([{ type: 'token', text: 'x' }])
  })

  it('skips a malformed frame without losing the rest of the stream', () => {
    const buffer = 'event: token\ndata: {not json\n\n' + frame('token', { text: 'survived' })
    const { events } = drainBuffer(buffer)
    expect(events).toEqual([{ type: 'token', text: 'survived' }])
  })

  it('joins multi-line data fields with newlines', () => {
    const { events } = drainBuffer('event: token\ndata: {"text":\ndata: "split"}\n\n')
    expect(events).toEqual([{ type: 'token', text: 'split' }])
  })
})

// --------------------------------------------------------------------------- streaming

describe('readEventStream', () => {
  const conversation =
    frame('session', { session_id: 'abc-123' }) +
    frame('sources', { chunks: [{ id: '1', title: 'Anaemia' }] }) +
    frame('token', { text: 'Iron ' }) +
    frame('token', { text: 'deficiency.' }) +
    frame('done', { provider: 'groq', latency_ms: 1200, red_flag: false })

  it('yields the documented event sequence', async () => {
    const events = await collect(conversation)
    expect(events.map((e) => e.type)).toEqual(['session', 'sources', 'token', 'token', 'done'])
  })

  it('produces identical output however the bytes are chunked', async () => {
    const whole = await collect(conversation)
    for (const size of [1, 3, 7, 16, 64]) {
      expect(await collect(conversation, size)).toEqual(whole)
    }
  })

  it('reassembles a token split across chunk boundaries', async () => {
    const events = await collect(conversation, 1)
    const text = events
      .filter((e): e is { type: 'token'; text: string } => e.type === 'token')
      .map((e) => e.text)
      .join('')
    expect(text).toBe('Iron deficiency.')
  })

  it('decodes multi-byte characters split across chunks', async () => {
    // 'é' and '—' are two and three bytes; a byte-at-a-time reader must not
    // turn them into replacement characters.
    const text = 'café — fièvre – 100–400'
    const events = await collect(frame('token', { text }), 1)
    expect(events).toEqual([{ type: 'token', text }])
  })

  it('emits a trailing event that has no blank line after it', async () => {
    const events = await collect('event: done\ndata: {"provider":"groq"}')
    expect(events).toEqual([{ type: 'done', provider: 'groq' }])
  })

  it('handles an empty stream', async () => {
    expect(await collect('')).toEqual([])
  })

  it('surfaces error events rather than throwing', async () => {
    const events = await collect(
      frame('error', { code: 'RATE_LIMITED', message: 'Too many', retry_after_s: 34 }),
    )
    expect(events).toEqual([
      { type: 'error', code: 'RATE_LIMITED', message: 'Too many', retry_after_s: 34 },
    ])
  })

  it('carries provider_switch through so the UI can reset', async () => {
    const stream =
      frame('token', { text: 'partial' }) +
      frame('provider_switch', { provider: 'gemini' }) +
      frame('token', { text: 'full answer' })
    const events = await collect(stream, 5)
    expect(events.map((e) => e.type)).toEqual(['token', 'provider_switch', 'token'])
  })

  it('stops early when aborted', async () => {
    const controller = new AbortController()
    controller.abort()
    const events = []
    for await (const e of readEventStream(streamOf(conversation), controller.signal)) {
      events.push(e)
    }
    expect(events).toEqual([])
  })
})
