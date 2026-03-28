import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useDateRange } from '@/hooks/useDateRange'
import { useBenchmarks, useAllDeveloperStats } from '@/hooks/useStats'
import { useDevelopers } from '@/hooks/useDevelopers'
import ErrorCard from '@/components/ErrorCard'
import StatCardSkeleton from '@/components/StatCardSkeleton'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import type { BenchmarkMetric, Developer, DeveloperStatsWithPercentiles, ReviewBreakdown } from '@/utils/types'

// Metric display config
interface MetricConfig {
  label: string
  lowerIsBetter: boolean
  format: (v: number) => string
}

const metricConfigs: Record<string, MetricConfig> = {
  prs_merged: { label: 'PRs Merged', lowerIsBetter: false, format: (v) => v.toFixed(0) },
  time_to_merge_h: { label: 'Time to Merge (h)', lowerIsBetter: true, format: (v) => v.toFixed(1) },
  time_to_first_review_h: { label: 'Time to First Review (h)', lowerIsBetter: true, format: (v) => v.toFixed(1) },
  time_to_approve_h: { label: 'Time to Approve (h)', lowerIsBetter: true, format: (v) => v.toFixed(1) },
  time_after_approve_h: { label: 'Post-Approval Merge (h)', lowerIsBetter: true, format: (v) => v.toFixed(1) },
  reviews_given: { label: 'Reviews Given', lowerIsBetter: false, format: (v) => v.toFixed(0) },
  review_turnaround_h: { label: 'Review Turnaround (h)', lowerIsBetter: true, format: (v) => v.toFixed(1) },
  additions_per_pr: { label: 'Additions per PR', lowerIsBetter: false, format: (v) => v.toFixed(0) },
  review_rounds: { label: 'Review Rounds', lowerIsBetter: true, format: (v) => v.toFixed(1) },
}

// Percentile band styles
const bandStyles = {
  above_p75: { normal: 'bg-emerald-500/10 text-emerald-600', label: 'Top 25%' },
  p50_to_p75: { normal: 'bg-emerald-500/5 text-emerald-600', label: '50th–75th' },
  p25_to_p50: { normal: 'bg-amber-500/10 text-amber-600', label: '25th–50th' },
  below_p25: { normal: 'bg-red-500/10 text-red-600', label: 'Bottom 25%' },
}

type Band = keyof typeof bandStyles

function getBand(value: number, metric: BenchmarkMetric, lowerIsBetter: boolean): Band {
  if (lowerIsBetter) {
    if (value <= metric.p25) return 'above_p75'
    if (value <= metric.p50) return 'p50_to_p75'
    if (value <= metric.p75) return 'p25_to_p50'
    return 'below_p25'
  }
  if (value >= metric.p75) return 'above_p75'
  if (value >= metric.p50) return 'p50_to_p75'
  if (value >= metric.p25) return 'p25_to_p50'
  return 'below_p25'
}

// Map benchmark metric key → field on DeveloperStatsWithPercentiles
const metricToStatsField: Record<string, string> = {
  prs_merged: 'prs_merged',
  time_to_merge_h: 'avg_time_to_merge_hours',
  time_to_first_review_h: 'avg_time_to_first_review_hours',
  time_to_approve_h: 'avg_time_to_approve_hours',
  time_after_approve_h: 'avg_time_after_approve_hours',
  reviews_given: 'reviews_given',
}

function extractMetricValue(
  stats: DeveloperStatsWithPercentiles,
  metricKey: string,
): number | null {
  // Try percentiles first (backend returns these for the matching key)
  const placement = stats.percentiles?.[metricKey]
  if (placement) return placement.value

  // Fallback to raw stats field
  const field = metricToStatsField[metricKey]
  if (!field) return null

  const raw = stats[field as keyof DeveloperStatsWithPercentiles]
  if (typeof raw === 'number') return raw
  // reviews_given is ReviewBreakdown
  if (raw && typeof raw === 'object' && 'approved' in raw) {
    const rb = raw as ReviewBreakdown
    return rb.approved + rb.changes_requested + rb.commented
  }
  return null
}

const bandBarColors: Record<Band, string> = {
  above_p75: 'bg-emerald-500',
  p50_to_p75: 'bg-emerald-400',
  p25_to_p50: 'bg-amber-400',
  below_p25: 'bg-red-400',
}

export default function Benchmarks() {
  const { dateFrom, dateTo } = useDateRange()
  const [teamFilter, setTeamFilter] = useState<string>('')
  const [selectedMetric, setSelectedMetric] = useState<string>('prs_merged')

  const { data: benchmarks, isLoading: benchmarksLoading, isError, refetch } = useBenchmarks(teamFilter || undefined, dateFrom, dateTo)
  const { data: developers } = useDevelopers()

  const activeDeveloperIds = useMemo(() => {
    if (!developers) return []
    return developers.filter((d) => d.is_active).map((d) => d.id)
  }, [developers])

  // Single batch hook — fetches all developer stats in parallel (TanStack useQueries)
  const devStatsResults = useAllDeveloperStats(activeDeveloperIds, dateFrom, dateTo)
  const devStatsLoading = devStatsResults.some((r) => r.isLoading)

  // Build a map of developer_id → stats for ranking
  const devStatsMap = useMemo(() => {
    const map = new Map<number, DeveloperStatsWithPercentiles>()
    devStatsResults.forEach((result, i) => {
      if (result.data) {
        map.set(activeDeveloperIds[i], result.data)
      }
    })
    return map
  }, [devStatsResults, activeDeveloperIds])

  const teams = useMemo(() => {
    if (!developers) return []
    const set = new Set(developers.map((d) => d.team).filter(Boolean) as string[])
    return Array.from(set).sort()
  }, [developers])

  const availableMetrics = useMemo(() => {
    if (!benchmarks) return []
    return Object.keys(benchmarks.metrics).filter((k) => k in metricConfigs)
  }, [benchmarks])

  // Build sorted ranking for selected metric
  const ranking = useMemo(() => {
    if (!developers || !benchmarks || !selectedMetric) return []
    const benchmark = benchmarks.metrics[selectedMetric]
    if (!benchmark) return []
    const config = metricConfigs[selectedMetric]

    const entries: { developer: Developer; value: number | null; band: Band }[] = []
    for (const dev of developers.filter((d) => d.is_active)) {
      const stats = devStatsMap.get(dev.id)
      let value: number | null = null
      let band: Band = 'p25_to_p50'

      if (stats) {
        value = extractMetricValue(stats, selectedMetric)
        if (value != null) {
          band = getBand(value, benchmark, config.lowerIsBetter)
        }
      }
      entries.push({ developer: dev, value, band })
    }

    // Sort: developers with values first, sorted by value (best first)
    entries.sort((a, b) => {
      if (a.value == null && b.value == null) return 0
      if (a.value == null) return 1
      if (b.value == null) return -1
      return config.lowerIsBetter ? a.value - b.value : b.value - a.value
    })

    return entries
  }, [developers, benchmarks, selectedMetric, devStatsMap])

  if (isError) {
    return <ErrorCard message="Could not load benchmark data." onRetry={refetch} />
  }

  const isLoading = benchmarksLoading || devStatsLoading

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Team Benchmarks</h1>
        <Skeleton className="h-48 w-full rounded-lg" />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <StatCardSkeleton key={i} />)}
        </div>
      </div>
    )
  }

  if (!benchmarks || Object.keys(benchmarks.metrics).length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Team Benchmarks</h1>
        <p className="text-muted-foreground">Not enough data to compute benchmarks. Need at least 3 developers with activity.</p>
      </div>
    )
  }

  const selectedBenchmark = benchmarks.metrics[selectedMetric]
  const selectedConfig = metricConfigs[selectedMetric]
  const maxDisplay = selectedBenchmark ? (selectedBenchmark.p75 * 1.5 || 1) : 1

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Team Benchmarks</h1>
          <p className="text-sm text-muted-foreground">
            {benchmarks.sample_size} developer{benchmarks.sample_size !== 1 ? 's' : ''} in sample
          </p>
        </div>
        {teams.length > 0 && (
          <select
            value={teamFilter}
            onChange={(e) => setTeamFilter(e.target.value)}
            className="rounded-md border bg-background px-2 py-1 text-sm"
          >
            <option value="">All teams</option>
            {teams.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        )}
      </div>

      {/* Percentile summary table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Percentile Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metric</TableHead>
                <TableHead className="text-right">p25</TableHead>
                <TableHead className="text-right">p50 (median)</TableHead>
                <TableHead className="text-right">p75</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {availableMetrics.map((key) => {
                const config = metricConfigs[key]
                const m = benchmarks.metrics[key]
                return (
                  <TableRow
                    key={key}
                    className={cn(
                      'cursor-pointer transition-colors',
                      selectedMetric === key && 'bg-muted'
                    )}
                    onClick={() => setSelectedMetric(key)}
                  >
                    <TableCell className="font-medium">{config.label}</TableCell>
                    <TableCell className="text-right">{config.format(m.p25)}</TableCell>
                    <TableCell className="text-right font-medium">{config.format(m.p50)}</TableCell>
                    <TableCell className="text-right">{config.format(m.p75)}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Developer ranking for selected metric */}
      {selectedBenchmark && selectedConfig && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Developer Ranking: {selectedConfig.label}
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              {selectedConfig.lowerIsBetter ? 'Lower is better' : 'Higher is better'}
              {' — '}p25: {selectedConfig.format(selectedBenchmark.p25)}, median: {selectedConfig.format(selectedBenchmark.p50)}, p75: {selectedConfig.format(selectedBenchmark.p75)}
            </p>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {ranking.map(({ developer, value, band }) => {
                const barWidth = value != null ? Math.min((value / maxDisplay) * 100, 100) : 0
                const bandStyle = bandStyles[band]

                return (
                  <div key={developer.id} className="flex items-center gap-3 py-1.5">
                    <Link
                      to={`/team/${developer.id}`}
                      className="w-32 shrink-0 truncate text-sm font-medium text-primary hover:underline"
                    >
                      {developer.display_name}
                    </Link>
                    <div className="flex-1">
                      <div className="h-4 w-full rounded-full bg-muted overflow-hidden">
                        <div
                          className={cn('h-full rounded-full transition-all', bandBarColors[band])}
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>
                    </div>
                    <span className="w-16 text-right text-sm font-mono">
                      {value != null ? selectedConfig.format(value) : '—'}
                    </span>
                    <Badge variant="secondary" className={cn('w-20 justify-center text-[10px]', bandStyle.normal)}>
                      {bandStyle.label}
                    </Badge>
                  </div>
                )
              })}
              {ranking.length === 0 && (
                <p className="text-sm text-muted-foreground py-4 text-center">No developer data available.</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
