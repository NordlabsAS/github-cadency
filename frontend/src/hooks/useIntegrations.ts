import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiFetch } from '@/utils/api'
import type {
  IntegrationConfig,
  IntegrationConfigCreate,
  IntegrationConfigUpdate,
  IntegrationTestResponse,
  IntegrationSyncStatus,
  IssueSourceResponse,
  LinearUserListResponse,
  MapUserRequest,
  DeveloperIdentityMap,
} from '@/utils/types'

export function useIntegrations() {
  return useQuery<IntegrationConfig[]>({
    queryKey: ['integrations'],
    queryFn: () => apiFetch('/integrations'),
    enabled: !!localStorage.getItem('devpulse_token'),
    staleTime: 30_000,
  })
}

export function useCreateIntegration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: IntegrationConfigCreate) =>
      apiFetch<IntegrationConfig>('/integrations', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['integrations'] })
      toast.success('Integration created')
    },
    onError: () => toast.error('Failed to create integration'),
  })
}

export function useUpdateIntegration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, updates }: { id: number; updates: IntegrationConfigUpdate }) =>
      apiFetch<IntegrationConfig>(`/integrations/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['integrations'] })
      toast.success('Integration updated')
    },
    onError: () => toast.error('Failed to update integration'),
  })
}

export function useDeleteIntegration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/integrations/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['integrations'] })
      toast.success('Integration removed')
    },
    onError: () => toast.error('Failed to remove integration'),
  })
}

export function useTestIntegration() {
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<IntegrationTestResponse>(`/integrations/${id}/test`, { method: 'POST' }),
    onSuccess: (data) => {
      if (data.success) toast.success(data.message)
      else toast.error(data.message)
    },
    onError: () => toast.error('Failed to test connection'),
  })
}

export function useTriggerSync() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/integrations/${id}/sync`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['integration-sync-status'] })
      toast.success('Sync started')
    },
    onError: () => toast.error('Failed to start sync'),
  })
}

export function useIntegrationSyncStatus(id: number | undefined) {
  return useQuery<IntegrationSyncStatus>({
    queryKey: ['integration-sync-status', id],
    queryFn: () => apiFetch(`/integrations/${id}/status`),
    enabled: !!id,
    staleTime: 10_000,
    refetchInterval: (query) =>
      query.state.data?.is_syncing ? 3_000 : false,
  })
}

export function useLinearUsers(id: number | undefined) {
  return useQuery<LinearUserListResponse>({
    queryKey: ['linear-users', id],
    queryFn: () => apiFetch(`/integrations/${id}/users`),
    enabled: !!id,
    staleTime: 60_000,
  })
}

export function useMapUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ integrationId, ...body }: MapUserRequest & { integrationId: number }) =>
      apiFetch<DeveloperIdentityMap>(`/integrations/${integrationId}/map-user`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['linear-users'] })
      toast.success('User mapped')
    },
    onError: () => toast.error('Failed to map user'),
  })
}

export function useIssueSource() {
  return useQuery<IssueSourceResponse>({
    queryKey: ['issue-source'],
    queryFn: () => apiFetch('/integrations/issue-source'),
    staleTime: 30_000,
  })
}

export function useSetPrimarySource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<IntegrationConfig>(`/integrations/${id}/primary`, { method: 'PATCH' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['integrations'] })
      qc.invalidateQueries({ queryKey: ['issue-source'] })
      toast.success('Primary issue source updated')
    },
    onError: () => toast.error('Failed to update primary source'),
  })
}
