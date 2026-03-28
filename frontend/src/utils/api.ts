const BASE_URL = '/api'

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
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }

  return res.json()
}
