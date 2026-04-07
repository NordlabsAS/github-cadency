import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/utils/api'
import type {
  ExternalSprint,
  SprintDetail,
  SprintVelocityResponse,
  SprintCompletionResponse,
  ScopeCreepResponse,
  ExternalProject,
  ExternalProjectDetail,
  TriageMetrics,
  EstimationAccuracyResponse,
  WorkAlignment,
  PlanningCorrelationResponse,
} from '@/utils/types'

export function useSprints(teamKey?: string, state?: string, limit = 20) {
  const params = new URLSearchParams()
  if (teamKey) params.set('team_key', teamKey)
  if (state) params.set('state', state)
  params.set('limit', String(limit))
  return useQuery<ExternalSprint[]>({
    queryKey: ['sprints', teamKey, state, limit],
    queryFn: () => apiFetch(`/sprints?${params}`),
    staleTime: 30_000,
  })
}

export function useSprintDetail(id: number | undefined) {
  return useQuery<SprintDetail>({
    queryKey: ['sprint-detail', id],
    queryFn: () => apiFetch(`/sprints/${id}`),
    enabled: !!id,
    staleTime: 30_000,
  })
}

export function useSprintVelocity(teamKey?: string, limit = 10) {
  const params = new URLSearchParams()
  if (teamKey) params.set('team_key', teamKey)
  params.set('limit', String(limit))
  return useQuery<SprintVelocityResponse>({
    queryKey: ['sprint-velocity', teamKey, limit],
    queryFn: () => apiFetch(`/sprints/velocity?${params}`),
    staleTime: 30_000,
  })
}

export function useSprintCompletion(teamKey?: string, limit = 10) {
  const params = new URLSearchParams()
  if (teamKey) params.set('team_key', teamKey)
  params.set('limit', String(limit))
  return useQuery<SprintCompletionResponse>({
    queryKey: ['sprint-completion', teamKey, limit],
    queryFn: () => apiFetch(`/sprints/completion?${params}`),
    staleTime: 30_000,
  })
}

export function useScopeCreep(teamKey?: string, limit = 10) {
  const params = new URLSearchParams()
  if (teamKey) params.set('team_key', teamKey)
  params.set('limit', String(limit))
  return useQuery<ScopeCreepResponse>({
    queryKey: ['scope-creep', teamKey, limit],
    queryFn: () => apiFetch(`/sprints/scope-creep?${params}`),
    staleTime: 30_000,
  })
}

export function useProjects() {
  return useQuery<ExternalProject[]>({
    queryKey: ['external-projects'],
    queryFn: () => apiFetch('/projects'),
    staleTime: 30_000,
  })
}

export function useProjectDetail(id: number | undefined) {
  return useQuery<ExternalProjectDetail>({
    queryKey: ['external-project', id],
    queryFn: () => apiFetch(`/projects/${id}`),
    enabled: !!id,
    staleTime: 30_000,
  })
}

export function useTriageMetrics(dateFrom?: string, dateTo?: string) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return useQuery<TriageMetrics>({
    queryKey: ['triage-metrics', dateFrom, dateTo],
    queryFn: () => apiFetch(`/planning/triage?${params}`),
    staleTime: 30_000,
  })
}

export function useEstimationAccuracy(teamKey?: string, limit = 10) {
  const params = new URLSearchParams()
  if (teamKey) params.set('team_key', teamKey)
  params.set('limit', String(limit))
  return useQuery<EstimationAccuracyResponse>({
    queryKey: ['estimation-accuracy', teamKey, limit],
    queryFn: () => apiFetch(`/planning/accuracy?${params}`),
    staleTime: 30_000,
  })
}

export function useWorkAlignment(dateFrom?: string, dateTo?: string) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return useQuery<WorkAlignment>({
    queryKey: ['work-alignment', dateFrom, dateTo],
    queryFn: () => apiFetch(`/planning/alignment?${params}`),
    staleTime: 30_000,
  })
}

export function usePlanningCorrelation(teamKey?: string, limit = 10) {
  const params = new URLSearchParams()
  if (teamKey) params.set('team_key', teamKey)
  params.set('limit', String(limit))
  return useQuery<PlanningCorrelationResponse>({
    queryKey: ['planning-correlation', teamKey, limit],
    queryFn: () => apiFetch(`/planning/correlation?${params}`),
    staleTime: 30_000,
  })
}

export interface DeveloperSprintSummary {
  active_sprint: {
    sprint_id: number
    name: string
    start_date: string | null
    end_date: string | null
    total_issues: number
    completed_issues: number
    completion_pct: number
    days_remaining: number
    on_track: boolean
  } | null
  recent_sprints: {
    sprint_id: number
    name: string
    total_issues: number
    completed_issues: number
    completion_pct: number
  }[]
}

export function useDeveloperSprintSummary(developerId?: number) {
  return useQuery<DeveloperSprintSummary>({
    queryKey: ['developer-sprint-summary', developerId],
    queryFn: () => apiFetch(`/developers/${developerId}/sprint-summary`),
    staleTime: 30_000,
    enabled: !!developerId,
  })
}

export interface DeveloperLinearIssue {
  id: number
  identifier: string
  title: string
  status: string | null
  status_category: string | null
  priority: number
  priority_label: string | null
  estimate: number | null
  url: string | null
  sprint_id: number | null
}

export function useDeveloperLinearIssues(developerId?: number, statusCategory?: string) {
  const params = new URLSearchParams()
  if (statusCategory) params.set('status_category', statusCategory)
  return useQuery<DeveloperLinearIssue[]>({
    queryKey: ['developer-linear-issues', developerId, statusCategory],
    queryFn: () => apiFetch(`/developers/${developerId}/linear-issues?${params}`),
    staleTime: 30_000,
    enabled: !!developerId,
  })
}
