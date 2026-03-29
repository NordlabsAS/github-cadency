import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiFetch } from '@/utils/api'
import type {
  DeveloperRelationshipResponse,
  DeveloperRelationshipsResponse,
  OrgTreeResponse,
  RelationshipType,
  WorksWithResponse,
} from '@/utils/types'

export function useRelationships(developerId: number) {
  return useQuery<DeveloperRelationshipsResponse>({
    queryKey: ['relationships', developerId],
    queryFn: () => apiFetch(`/developers/${developerId}/relationships`),
    enabled: !!developerId,
  })
}

export function useCreateRelationship(developerId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { target_id: number; relationship_type: RelationshipType }) =>
      apiFetch<DeveloperRelationshipResponse>(
        `/developers/${developerId}/relationships`,
        { method: 'POST', body: JSON.stringify(data) }
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['relationships', developerId] })
      qc.invalidateQueries({ queryKey: ['org-tree'] })
      toast.success('Relationship added')
    },
    onError: () => toast.error('Failed to add relationship'),
  })
}

export function useDeleteRelationship(developerId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { target_id: number; relationship_type: RelationshipType }) =>
      apiFetch(`/developers/${developerId}/relationships`, {
        method: 'DELETE',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['relationships', developerId] })
      qc.invalidateQueries({ queryKey: ['org-tree'] })
      toast.success('Relationship removed')
    },
    onError: () => toast.error('Failed to remove relationship'),
  })
}

export function useOrgTree(team?: string) {
  const params = new URLSearchParams()
  if (team) params.set('team', team)
  return useQuery<OrgTreeResponse>({
    queryKey: ['org-tree', team],
    queryFn: () => apiFetch(`/org-tree?${params}`),
  })
}

export function useWorksWith(developerId: number, dateFrom?: string, dateTo?: string) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return useQuery<WorksWithResponse>({
    queryKey: ['works-with', developerId, dateFrom, dateTo],
    queryFn: () => apiFetch(`/developers/${developerId}/works-with?${params}`),
    enabled: !!developerId,
  })
}
