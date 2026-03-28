import { createContext, useContext } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/utils/api'
import type { AuthUser } from '@/utils/types'

export interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  isAdmin: boolean
  login: () => void
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function useAuthProvider(): AuthContextValue {
  const queryClient = useQueryClient()
  const token = localStorage.getItem('devpulse_token')

  const { data: user = null, isLoading } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => apiFetch<AuthUser>('/auth/me'),
    enabled: !!token,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const login = async () => {
    const data = await apiFetch<{ url: string }>('/auth/login')
    window.location.href = data.url
  }

  const logout = () => {
    localStorage.removeItem('devpulse_token')
    queryClient.clear()
    window.location.href = '/login'
  }

  return {
    user,
    isLoading,
    isAdmin: user?.app_role === 'admin',
    login,
    logout,
  }
}
