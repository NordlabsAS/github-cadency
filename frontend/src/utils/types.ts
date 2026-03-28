// --- Auth ---

export interface AuthUser {
  developer_id: number
  github_username: string
  display_name: string
  app_role: 'admin' | 'developer'
  avatar_url: string | null
}

// --- Developer ---

export interface Developer {
  id: number
  github_username: string
  display_name: string
  email: string | null
  role: string | null
  skills: string[] | null
  specialty: string | null
  location: string | null
  timezone: string | null
  team: string | null
  app_role: string
  is_active: boolean
  avatar_url: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface DeveloperCreate {
  github_username: string
  display_name: string
  email?: string | null
  role?: string | null
  skills?: string[] | null
  specialty?: string | null
  location?: string | null
  timezone?: string | null
  team?: string | null
  notes?: string | null
}

export type DeveloperUpdate = Partial<Omit<DeveloperCreate, 'github_username'>>

// --- Stats ---

export interface ReviewBreakdown {
  approved: number
  changes_requested: number
  commented: number
}

export interface DeveloperStats {
  prs_opened: number
  prs_merged: number
  prs_closed_without_merge: number
  prs_open: number
  prs_draft: number
  total_additions: number
  total_deletions: number
  total_changed_files: number
  reviews_given: ReviewBreakdown
  reviews_received: number
  avg_time_to_first_review_hours: number | null
  avg_time_to_merge_hours: number | null
  issues_assigned: number
  issues_closed: number
  avg_time_to_close_issue_hours: number | null
  avg_time_to_approve_hours: number | null
  avg_time_after_approve_hours: number | null
  prs_merged_without_approval: number
  prs_reverted: number
  reverts_authored: number
}

export interface TeamStats {
  developer_count: number
  total_prs: number
  total_merged: number
  merge_rate: number | null
  avg_time_to_first_review_hours: number | null
  avg_time_to_merge_hours: number | null
  total_reviews: number
  total_issues_closed: number
  revert_rate: number | null
}

export interface TopContributor {
  developer_id: number
  github_username: string
  display_name: string
  pr_count: number
}

export interface RepoStats {
  total_prs: number
  total_merged: number
  total_issues: number
  total_issues_closed: number
  total_reviews: number
  avg_time_to_merge_hours: number | null
  top_contributors: TopContributor[]
}

// --- Repo ---

export interface Repo {
  id: number
  github_id: number
  name: string | null
  full_name: string | null
  description: string | null
  language: string | null
  is_tracked: boolean
  last_synced_at: string | null
  created_at: string
}

// --- Sync ---

export interface SyncEvent {
  id: number
  sync_type: string | null
  status: string | null
  repos_synced: number | null
  prs_upserted: number | null
  issues_upserted: number | null
  errors: Record<string, unknown> | null
  started_at: string | null
  completed_at: string | null
  duration_s: number | null
}

// --- AI Analysis ---

export interface AIAnalysis {
  id: number
  analysis_type: string | null
  scope_type: string | null
  scope_id: string | null
  date_from: string | null
  date_to: string | null
  input_summary: string | null
  result: Record<string, unknown> | null
  model_used: string | null
  tokens_used: number | null
  triggered_by: string | null
  created_at: string
}

export interface AIAnalyzeRequest {
  analysis_type: 'communication' | 'conflict' | 'sentiment'
  scope_type: 'developer' | 'team' | 'repo'
  scope_id: string
  date_from: string
  date_to: string
}

export interface OneOnOnePrepRequest {
  developer_id: number
  date_from: string
  date_to: string
}

export interface TeamHealthRequest {
  team?: string
  date_from: string
  date_to: string
}

// --- Review Quality (M1) ---

export interface ReviewQualityBreakdown {
  thorough: number
  standard: number
  minimal: number
  rubber_stamp: number
}

// --- Benchmarks / Percentiles (M2) ---

export interface BenchmarkMetric {
  p25: number
  p50: number
  p75: number
}

export interface PercentilePlacement {
  value: number
  percentile_band: 'below_p25' | 'p25_to_p50' | 'p50_to_p75' | 'above_p75'
  team_median: number
}

export interface DeveloperStatsWithPercentiles extends DeveloperStats {
  review_quality_breakdown?: ReviewQualityBreakdown
  review_quality_score?: number | null
  percentiles?: Record<string, PercentilePlacement> | null
}

// --- Trends (M3) ---

export interface TrendPeriod {
  start: string
  end: string
  prs_merged: number
  avg_time_to_merge_h: number | null
  reviews_given: number
  additions: number
  deletions: number
  issues_closed: number
}

export interface TrendDirection {
  direction: 'improving' | 'stable' | 'worsening'
  change_pct: number
}

export interface DeveloperTrendsResponse {
  developer_id: number
  period_type: string
  periods: TrendPeriod[]
  trends: Record<string, TrendDirection>
}

// --- Workload (M4) ---

export interface DeveloperWorkload {
  developer_id: number
  github_username: string
  display_name: string
  open_prs_authored: number
  drafts_open: number
  open_prs_reviewing: number
  open_issues_assigned: number
  reviews_given_this_period: number
  reviews_received_this_period: number
  prs_waiting_for_review: number
  avg_review_wait_h: number | null
  workload_score: 'low' | 'balanced' | 'high' | 'overloaded'
}

export interface WorkloadAlert {
  type: 'review_bottleneck' | 'stale_prs' | 'uneven_assignment' | 'underutilized' | 'merged_without_approval' | 'revert_spike'
  developer_id: number | null
  message: string
}

export interface WorkloadResponse {
  developers: DeveloperWorkload[]
  alerts: WorkloadAlert[]
}

// --- Stale PRs (P2-01) ---

export interface StalePR {
  pr_id: number
  number: number
  title: string
  html_url: string
  repo_name: string
  author_name: string | null
  author_id: number | null
  age_hours: number
  is_draft: boolean
  review_count: number
  has_approved: boolean
  has_changes_requested: boolean
  last_activity_at: string
  stale_reason: 'no_review' | 'changes_requested_no_response' | 'approved_not_merged'
}

export interface StalePRsResponse {
  stale_prs: StalePR[]
  total_count: number
}

// --- Goals (M6 + P1-03) ---

export type GoalMetricKey =
  | 'avg_pr_additions'
  | 'time_to_merge_h'
  | 'reviews_given'
  | 'review_quality_score'
  | 'prs_merged'
  | 'time_to_first_review_h'
  | 'issues_closed'
  | 'prs_opened'

export interface GoalResponse {
  id: number
  developer_id: number
  title: string
  description: string | null
  metric_key: string
  target_value: number
  target_direction: string
  baseline_value: number | null
  status: string
  created_at: string
  target_date: string | null
  achieved_at: string | null
  notes: string | null
  created_by: string | null
}

export interface GoalSelfCreate {
  title: string
  description?: string | null
  metric_key: GoalMetricKey
  target_value: number
  target_direction?: 'above' | 'below'
  target_date?: string | null
}

export interface GoalAdminCreate extends GoalSelfCreate {
  developer_id: number
}

export interface GoalSelfUpdate {
  target_value?: number | null
  target_date?: string | null
  status?: 'active' | 'achieved' | 'abandoned' | null
  notes?: string | null
}

export interface GoalProgressPoint {
  period_end: string
  value: number
}

export interface GoalProgressResponse {
  goal_id: number
  title: string
  target_value: number
  target_direction: string
  baseline_value: number | null
  current_value: number | null
  status: string
  history: GoalProgressPoint[]
}
