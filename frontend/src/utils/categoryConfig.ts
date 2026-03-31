/**
 * Fallback category config used while dynamic categories load from the API.
 * Prefer useCategoryConfig() from @/hooks/useWorkCategories for dynamic data.
 */
export const FALLBACK_CATEGORY_CONFIG: Record<string, { label: string; color: string }> = {
  feature: { label: 'Feature', color: '#3b82f6' },
  bugfix: { label: 'Bug Fix', color: '#ef4444' },
  tech_debt: { label: 'Tech Debt', color: '#f59e0b' },
  ops: { label: 'Ops', color: '#22c55e' },
  unknown: { label: 'Unknown', color: '#94a3b8' },
}

export const FALLBACK_CATEGORY_ORDER: string[] = ['feature', 'bugfix', 'tech_debt', 'ops', 'unknown']
