import { logger } from '@/utils/logger'

const BASE_URL = '/api'

export class ApiError extends Error {
  status: number
  detail: any

  constructor(status: number, detail: any) {
    super(typeof detail === 'string' ? detail : detail?.message ?? `HTTP ${status}`)
    this.status = status
    this.detail = detail
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const token = localStorage.getItem('devpulse_token')

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  })

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('devpulse_token')
      window.location.href = '/login'
      throw new Error('Session expired')
    }
    let detail: any
    try {
      const body = await res.json()
      detail = body.detail ?? body
    } catch {
      detail = await res.text()
    }
    logger.error('API request failed', {
      status: res.status,
      path,
      detail: typeof detail === 'string' ? detail : detail?.message ?? String(detail),
    })
    throw new ApiError(res.status, detail)
  }

  return res.json()
}
