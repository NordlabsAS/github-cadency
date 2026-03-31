import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiFetch } from '@/utils/api'

export interface WorkCategoryDef {
  category_key: string
  display_name: string
  description: string | null
  color: string
  exclude_from_stats: boolean
  display_order: number
  is_default: boolean
}

export interface WorkCategoryRuleDef {
  id: number
  match_type: 'label' | 'title_regex' | 'prefix' | 'issue_type'
  match_value: string
  description: string | null
  case_sensitive: boolean
  category_key: string
  priority: number
}

export interface ReclassifyResult {
  prs_updated: number
  issues_updated: number
  duration_s: number
}

// --- Categories ---

export function useWorkCategories() {
  return useQuery<WorkCategoryDef[]>({
    queryKey: ['work-categories'],
    queryFn: () => apiFetch('/work-categories'),
    staleTime: 5 * 60_000,
  })
}

export function useCreateWorkCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { category_key: string; display_name: string; description?: string | null; color: string; exclude_from_stats?: boolean }) =>
      apiFetch<WorkCategoryDef>('/work-categories', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-categories'] })
      toast.success('Category created')
    },
    onError: () => toast.error('Failed to create category'),
  })
}

export function useUpdateWorkCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ key, ...data }: { key: string; display_name?: string; description?: string | null; color?: string; exclude_from_stats?: boolean; display_order?: number }) =>
      apiFetch<WorkCategoryDef>(`/work-categories/${key}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-categories'] })
      toast.success('Category updated')
    },
    onError: () => toast.error('Failed to update category'),
  })
}

export function useDeleteWorkCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (key: string) =>
      apiFetch(`/work-categories/${key}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-categories'] })
      toast.success('Category deleted')
    },
    onError: () => toast.error('Failed to delete category'),
  })
}

// --- Rules ---

export function useWorkCategoryRules() {
  return useQuery<WorkCategoryRuleDef[]>({
    queryKey: ['work-category-rules'],
    queryFn: () => apiFetch('/work-categories/rules'),
    staleTime: 5 * 60_000,
  })
}

export function useCreateWorkCategoryRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Omit<WorkCategoryRuleDef, 'id'>) =>
      apiFetch<WorkCategoryRuleDef>('/work-categories/rules', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-category-rules'] })
      toast.success('Rule created')
    },
    onError: () => toast.error('Failed to create rule'),
  })
}

export function useUpdateWorkCategoryRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: number } & Partial<Omit<WorkCategoryRuleDef, 'id'>>) =>
      apiFetch<WorkCategoryRuleDef>(`/work-categories/rules/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-category-rules'] })
      toast.success('Rule updated')
    },
    onError: () => toast.error('Failed to update rule'),
  })
}

export function useDeleteWorkCategoryRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/work-categories/rules/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-category-rules'] })
      toast.success('Rule deleted')
    },
    onError: () => toast.error('Failed to delete rule'),
  })
}

// --- Suggestions ---

export interface WorkCategorySuggestion {
  match_type: 'label' | 'issue_type'
  match_value: string
  suggested_category: string
  usage_count: number
}

export function useScanSuggestions() {
  return useMutation({
    mutationFn: () =>
      apiFetch<WorkCategorySuggestion[]>('/work-categories/suggestions', { method: 'POST' }),
    onError: () => toast.error('Failed to scan GitHub data'),
  })
}

export function useBulkCreateRules() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (rules: Omit<WorkCategoryRuleDef, 'id'>[]) =>
      apiFetch<{ created: number }>('/work-categories/rules/bulk', {
        method: 'POST',
        body: JSON.stringify({ rules }),
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['work-category-rules'] })
      toast.success(`Created ${data.created} rule${data.created === 1 ? '' : 's'}`)
    },
    onError: () => toast.error('Failed to create rules'),
  })
}

// --- Reclassify ---

export function useReclassify() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<ReclassifyResult>('/work-categories/reclassify', { method: 'POST' }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['work-allocation'] })
      qc.invalidateQueries({ queryKey: ['work-allocation-items'] })
      toast.success(`Reclassified ${data.prs_updated} PRs and ${data.issues_updated} issues`)
    },
    onError: () => toast.error('Failed to reclassify'),
  })
}

// --- Derived config (replaces static CATEGORY_CONFIG) ---

export function useCategoryConfig() {
  const { data: categories } = useWorkCategories()
  return useMemo(() => {
    if (!categories) return null
    const config: Record<string, { label: string; color: string; excludeFromStats: boolean }> = {}
    const order: string[] = []
    for (const cat of [...categories].sort((a, b) => a.display_order - b.display_order)) {
      config[cat.category_key] = {
        label: cat.display_name,
        color: cat.color,
        excludeFromStats: cat.exclude_from_stats,
      }
      order.push(cat.category_key)
    }
    return { config, order }
  }, [categories])
}
