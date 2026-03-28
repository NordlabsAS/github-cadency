import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiFetch } from '@/utils/api'
import type { AIAnalysis, AIAnalyzeRequest, OneOnOnePrepRequest, TeamHealthRequest } from '@/utils/types'

export function useAIHistory() {
  return useQuery<AIAnalysis[]>({
    queryKey: ['ai-history'],
    queryFn: () => apiFetch('/ai/history'),
  })
}

export function useAIAnalysis(id: number) {
  return useQuery<AIAnalysis>({
    queryKey: ['ai-analysis', id],
    queryFn: () => apiFetch(`/ai/history/${id}`),
    enabled: !!id,
  })
}

export function useRunAnalysis() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AIAnalyzeRequest) =>
      apiFetch<AIAnalysis>('/ai/analyze', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ai-history'] })
      toast.success('Analysis started')
    },
    onError: () => toast.error('Analysis failed'),
  })
}

export function useRunOneOnOnePrep() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: OneOnOnePrepRequest) =>
      apiFetch<AIAnalysis>('/ai/one-on-one-prep', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ai-history'] })
      toast.success('1:1 prep brief generated')
    },
    onError: () => toast.error('Failed to generate 1:1 prep'),
  })
}

export function useRunTeamHealth() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TeamHealthRequest) =>
      apiFetch<AIAnalysis>('/ai/team-health', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ai-history'] })
      toast.success('Team health check generated')
    },
    onError: () => toast.error('Failed to generate team health check'),
  })
}
