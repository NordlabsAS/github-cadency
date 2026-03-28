import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiFetch } from '@/utils/api'
import type {
  GoalResponse,
  GoalProgressResponse,
  GoalSelfCreate,
  GoalAdminCreate,
  GoalSelfUpdate,
  GoalAdminUpdate,
} from '@/utils/types'

export function useGoals(developerId: number) {
  return useQuery<GoalResponse[]>({
    queryKey: ['goals', developerId],
    queryFn: () => apiFetch(`/goals?developer_id=${developerId}`),
    enabled: !!developerId,
  })
}

export function useGoalProgress(goalId: number) {
  return useQuery<GoalProgressResponse>({
    queryKey: ['goal-progress', goalId],
    queryFn: () => apiFetch(`/goals/${goalId}/progress`),
    enabled: !!goalId,
  })
}

export function useCreateSelfGoal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: GoalSelfCreate) =>
      apiFetch<GoalResponse>('/goals/self', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goals'] })
      toast.success('Goal created')
    },
    onError: () => toast.error('Failed to create goal'),
  })
}

export function useCreateAdminGoal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: GoalAdminCreate) =>
      apiFetch<GoalResponse>('/goals', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goals'] })
      toast.success('Goal created')
    },
    onError: () => toast.error('Failed to create goal'),
  })
}

export function useUpdateAdminGoal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ goalId, data }: { goalId: number; data: GoalAdminUpdate }) =>
      apiFetch<GoalResponse>(`/goals/${goalId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goals'] })
      qc.invalidateQueries({ queryKey: ['goal-progress'] })
      toast.success('Goal updated')
    },
    onError: () => toast.error('Failed to update goal'),
  })
}

export function useUpdateSelfGoal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ goalId, data }: { goalId: number; data: GoalSelfUpdate }) =>
      apiFetch<GoalResponse>(`/goals/self/${goalId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goals'] })
      qc.invalidateQueries({ queryKey: ['goal-progress'] })
      toast.success('Goal updated')
    },
    onError: () => toast.error('Failed to update goal'),
  })
}
