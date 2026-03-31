/**
 * Structured frontend logger — batches entries and ships to backend.
 *
 * Only warn/error are shipped; debug/info are console-only.
 * Uses navigator.sendBeacon on page unload for reliability.
 */

interface LogEntry {
  level: 'warn' | 'error'
  message: string
  event_type: string
  context?: Record<string, unknown>
  timestamp: string
  url: string
  user_agent: string
}

const FLUSH_INTERVAL_MS = 5_000
const FLUSH_THRESHOLD = 10
const INGEST_PATH = '/api/logs/ingest'

let buffer: LogEntry[] = []
let flushTimer: ReturnType<typeof setInterval> | null = null

function makeEntry(
  level: 'warn' | 'error',
  message: string,
  context?: Record<string, unknown>,
  eventType = 'frontend.error',
): LogEntry {
  return {
    level,
    message,
    event_type: eventType,
    context,
    timestamp: new Date().toISOString(),
    url: window.location.href,
    user_agent: navigator.userAgent,
  }
}

function flush() {
  if (buffer.length === 0) return

  const entries = buffer
  buffer = []

  const body = JSON.stringify({ entries })

  // Try sendBeacon first (works during page unload), fall back to fetch
  if (navigator.sendBeacon) {
    const sent = navigator.sendBeacon(INGEST_PATH, new Blob([body], { type: 'application/json' }))
    if (sent) return
  }

  fetch(INGEST_PATH, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    keepalive: true,
  }).catch(() => {
    // Silently drop — we can't log a logging failure
  })
}

function enqueue(entry: LogEntry) {
  buffer.push(entry)
  if (buffer.length >= FLUSH_THRESHOLD) {
    flush()
  }
}

function startFlushTimer() {
  if (flushTimer) return
  flushTimer = setInterval(flush, FLUSH_INTERVAL_MS)
}

/** Initialize global error handlers. Call once at app startup. */
export function initLogger() {
  startFlushTimer()

  window.addEventListener('beforeunload', flush)

  window.addEventListener('error', (event) => {
    logger.error(event.message, {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
    })
  })

  window.addEventListener('unhandledrejection', (event) => {
    const message =
      event.reason instanceof Error ? event.reason.message : String(event.reason)
    logger.error(`Unhandled promise rejection: ${message}`)
  })
}

export const logger = {
  error(message: string, context?: Record<string, unknown>) {
    console.error('[DevPulse]', message, context)
    enqueue(makeEntry('error', message, context))
  },

  warn(message: string, context?: Record<string, unknown>) {
    console.warn('[DevPulse]', message, context)
    enqueue(makeEntry('warn', message, context, 'frontend.warn'))
  },

  /** Console-only — not shipped to backend. */
  info(message: string, ...args: unknown[]) {
    console.info('[DevPulse]', message, ...args)
  },

  /** Console-only — not shipped to backend. */
  debug(message: string, ...args: unknown[]) {
    console.debug('[DevPulse]', message, ...args)
  },
}
