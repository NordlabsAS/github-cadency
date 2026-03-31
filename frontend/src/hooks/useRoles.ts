import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiFetch } from '@/utils/api'
import type { RoleDefinition } from '@/utils/types'

export function useRoles() {
  return useQuery<RoleDefinition[]>({
    queryKey: ['roles'],
    queryFn: () => apiFetch('/roles'),
    staleTime: 5 * 60_000,
  })
}

export function useCreateRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { role_key: string; display_name: string; contribution_category: string }) =>
      apiFetch<RoleDefinition>('/roles', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['roles'] })
      toast.success('Role created')
    },
    onError: () => toast.error('Failed to create role'),
  })
}

export function useUpdateRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ roleKey, ...data }: { roleKey: string; display_name?: string; contribution_category?: string; display_order?: number }) =>
      apiFetch<RoleDefinition>(`/roles/${roleKey}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['roles'] })
      toast.success('Role updated')
    },
    onError: () => toast.error('Failed to update role'),
  })
}

export function useDeleteRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (roleKey: string) =>
      apiFetch(`/roles/${roleKey}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['roles'] })
      toast.success('Role deleted')
    },
    onError: () => toast.error('Failed to delete role'),
  })
}
