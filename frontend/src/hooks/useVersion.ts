import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/utils/api'
import type { VersionInfo } from '@/utils/types'

export function useVersion() {
  return useQuery<VersionInfo>({
    queryKey: ['version'],
    queryFn: () => apiFetch('/system/version'),
    staleTime: 300_000,
  })
}
