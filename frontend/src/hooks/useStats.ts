import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/utils/api'
import type {
  DeveloperStatsWithPercentiles,
  DeveloperTrendsResponse,
  RepoStats,
  StalePRsResponse,
  TeamStats,
  WorkloadResponse,
} from '@/utils/types'

function dateParams(dateFrom?: string, dateTo?: string) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return params.toString()
}

export function useDeveloperStats(id: number, dateFrom?: string, dateTo?: string) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  params.set('include_percentiles', 'true')
  return useQuery<DeveloperStatsWithPercentiles>({
    queryKey: ['developer-stats', id, dateFrom, dateTo],
    queryFn: () => apiFetch(`/stats/developer/${id}?${params}`),
    enabled: !!id,
  })
}

export function useTeamStats(team?: string, dateFrom?: string, dateTo?: string) {
  const params = new URLSearchParams()
  if (team) params.set('team', team)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return useQuery<TeamStats>({
    queryKey: ['team-stats', team, dateFrom, dateTo],
    queryFn: () => apiFetch(`/stats/team?${params}`),
  })
}

export function useRepoStats(id: number, dateFrom?: string, dateTo?: string) {
  return useQuery<RepoStats>({
    queryKey: ['repo-stats', id, dateFrom, dateTo],
    queryFn: () => apiFetch(`/stats/repo/${id}?${dateParams(dateFrom, dateTo)}`),
    enabled: !!id,
  })
}

export function useDeveloperTrends(
  id: number,
  periodType: string = 'week',
  periods: number = 8,
) {
  const params = new URLSearchParams()
  params.set('period_type', periodType)
  params.set('periods', String(periods))
  return useQuery<DeveloperTrendsResponse>({
    queryKey: ['developer-trends', id, periodType, periods],
    queryFn: () => apiFetch(`/stats/developer/${id}/trends?${params}`),
    enabled: !!id,
  })
}

export function useStalePRs(team?: string, thresholdHours?: number) {
  const params = new URLSearchParams()
  if (team) params.set('team', team)
  if (thresholdHours) params.set('threshold_hours', String(thresholdHours))
  return useQuery<StalePRsResponse>({
    queryKey: ['stale-prs', team, thresholdHours],
    queryFn: () => apiFetch(`/stats/stale-prs?${params}`),
  })
}

export function useWorkload(team?: string, dateFrom?: string, dateTo?: string) {
  const params = new URLSearchParams()
  if (team) params.set('team', team)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return useQuery<WorkloadResponse>({
    queryKey: ['workload', team, dateFrom, dateTo],
    queryFn: () => apiFetch(`/stats/workload?${params}`),
  })
}
