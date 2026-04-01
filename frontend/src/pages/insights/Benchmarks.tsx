import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useDateRange } from '@/hooks/useDateRange'
import { useBenchmarkGroups, useBenchmarksV2 } from '@/hooks/useStats'
import { useDevelopers } from '@/hooks/useDevelopers'
import ErrorCard from '@/components/ErrorCard'
import StatCardSkeleton from '@/components/StatCardSkeleton'
import SortableHead from '@/components/SortableHead'
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
import type {
  BenchmarkMetric,
  BenchmarkMetricInfo,
  DeveloperBenchmarkRow,
} from '@/utils/types'

// Percentile band styles
const bandStyles = {
  above_p75: { color: 'bg-emerald-500/10 text-emerald-600', bar: 'bg-emerald-500', label: 'Top 25%' },
  p50_to_p75: { color: 'bg-emerald-500/5 text-emerald-600', bar: 'bg-emerald-400', label: '50th\u201375th' },
  p25_to_p50: { color: 'bg-amber-500/10 text-amber-600', bar: 'bg-amber-400', label: '25th\u201350th' },
  below_p25: { color: 'bg-red-500/10 text-red-600', bar: 'bg-red-400', label: 'Bottom 25%' },
} as const

type Band = keyof typeof bandStyles

function formatMetricValue(value: number | null, info: BenchmarkMetricInfo): string {
  if (value == null) return '\u2014'
  switch (info.unit) {
    case 'hours': return value.toFixed(1)
    case 'ratio': return (value * 100).toFixed(1) + '%'
    case 'percent': return value.toFixed(1) + '%'
    case 'score': return value.toFixed(1)
    case 'per_day': return value.toFixed(2)
    default: return value.toFixed(0)
  }
}

export default function Benchmarks() {
  const { dateFrom, dateTo } = useDateRange()
  const [searchParams, setSearchParams] = useSearchParams()
  const groupParam = searchParams.get('group') || undefined
  const teamParam = searchParams.get('team') || undefined
  const sortKey = searchParams.get('sort') || undefined
  const sortDir = (searchParams.get('dir') as 'asc' | 'desc') || undefined

  const { data: groups, isLoading: groupsLoading } = useBenchmarkGroups()
  const { data: benchmarks, isLoading: benchmarksLoading, isError, refetch } = useBenchmarksV2(
    groupParam, teamParam, dateFrom, dateTo
  )
  const { data: developers } = useDevelopers()

  // Extract unique team names from developers
  const teams = useMemo(() => {
    if (!developers) return []
    const set = new Set(developers.map((d) => d.team).filter(Boolean) as string[])
    return Array.from(set).sort()
  }, [developers])

  // Build metric info map for formatting
  const metricInfoMap = useMemo(() => {
    if (!benchmarks) return new Map<string, BenchmarkMetricInfo>()
    return new Map(benchmarks.metric_info.map((m) => [m.key, m]))
  }, [benchmarks])

  // Sort developers
  const sortedDevelopers = useMemo(() => {
    if (!benchmarks) return []
    const devs = [...benchmarks.developers]
    const key = sortKey || benchmarks.group.metrics[0]
    if (!key) return devs
    const info = metricInfoMap.get(key)
    const ascending = sortDir === 'asc' || (!sortDir && info?.lower_is_better)

    devs.sort((a, b) => {
      const av = a.metrics[key]?.value
      const bv = b.metrics[key]?.value
      if (av == null && bv == null) return 0
      if (av == null) return 1
      if (bv == null) return -1
      return ascending ? av - bv : bv - av
    })
    return devs
  }, [benchmarks, sortKey, sortDir, metricInfoMap])

  function updateParam(key: string, value: string | undefined) {
    const next = new URLSearchParams(searchParams)
    if (value) {
      next.set(key, value)
    } else {
      next.delete(key)
    }
    // Reset sort when switching group
    if (key === 'group') {
      next.delete('sort')
      next.delete('dir')
    }
    setSearchParams(next, { replace: true })
  }

  function handleSort(metricKey: string) {
    const next = new URLSearchParams(searchParams)
    if (sortKey === metricKey) {
      // Toggle direction
      next.set('dir', sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      next.set('sort', metricKey)
      const info = metricInfoMap.get(metricKey)
      next.set('dir', info?.lower_is_better ? 'asc' : 'desc')
    }
    setSearchParams(next, { replace: true })
  }

  if (isError) {
    return <ErrorCard message="Could not load benchmark data." onRetry={refetch} />
  }

  const isLoading = groupsLoading || benchmarksLoading

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Benchmarks</h1>
        <Skeleton className="h-10 w-full rounded-lg" />
        <Skeleton className="h-48 w-full rounded-lg" />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <StatCardSkeleton key={i} />)}
        </div>
      </div>
    )
  }

  const activeGroup = benchmarks?.group
  const unassignedBanner = benchmarks && benchmarks.sample_size === 0 && groups && groups.length > 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Benchmarks</h1>
          {benchmarks && (
            <p className="text-sm text-muted-foreground">
              {benchmarks.sample_size} developer{benchmarks.sample_size !== 1 ? 's' : ''} in{' '}
              {activeGroup?.display_name || 'group'}
              {benchmarks.team && ` \u00b7 ${benchmarks.team}`}
            </p>
          )}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2">
          {teams.length > 0 && (
            <select
              value={teamParam || ''}
              onChange={(e) => updateParam('team', e.target.value || undefined)}
              className="rounded-md border bg-background px-2 py-1.5 text-sm"
            >
              <option value="">All teams</option>
              {teams.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Group tabs */}
      {groups && groups.length > 0 && (
        <div className="flex gap-1 rounded-lg bg-muted p-1">
          {groups.map((g) => (
            <button
              key={g.group_key}
              onClick={() => updateParam('group', g.group_key === groups[0].group_key ? undefined : g.group_key)}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                (activeGroup?.group_key === g.group_key)
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {g.display_name}
            </button>
          ))}
        </div>
      )}

      {/* Empty state */}
      {unassignedBanner && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">
              No developers found with roles matching this group.{' '}
              <Link to="/admin/team" className="text-primary hover:underline">
                Assign roles in Team Registry
              </Link>{' '}
              to enable benchmarking.
            </p>
          </CardContent>
        </Card>
      )}

      {benchmarks && benchmarks.sample_size > 0 && (
        <>
          {/* Percentile Distribution */}
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
                  {benchmarks.metric_info.map((info) => {
                    const m = benchmarks.metrics[info.key]
                    if (!m) return null
                    return (
                      <TableRow key={info.key}>
                        <TableCell className="font-medium">{info.label}</TableCell>
                        <TableCell className="text-right">{formatMetricValue(m.p25, info)}</TableCell>
                        <TableCell className="text-right font-medium">{formatMetricValue(m.p50, info)}</TableCell>
                        <TableCell className="text-right">{formatMetricValue(m.p75, info)}</TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Developer Ranking Table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Developer Ranking</CardTitle>
              {benchmarks.sample_size < 3 && (
                <p className="text-xs text-amber-600">
                  Fewer than 3 developers \u2014 percentile bands may not be meaningful.
                </p>
              )}
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky left-0 bg-background">Developer</TableHead>
                      <TableHead>Team</TableHead>
                      {benchmarks.metric_info.map((info) => (
                        <SortableHead
                          key={info.key}
                          field={info.key}
                          current={sortKey || benchmarks.group.metrics[0]}
                          asc={
                            (sortKey || benchmarks.group.metrics[0]) === info.key
                              ? (sortDir || (info.lower_is_better ? 'asc' : 'desc')) === 'asc'
                              : false
                          }
                          onToggle={() => handleSort(info.key)}
                          className="text-right"
                        >
                          {info.label}
                        </SortableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedDevelopers.map((dev) => (
                      <DeveloperRow
                        key={dev.developer_id}
                        dev={dev}
                        metricInfoList={benchmarks.metric_info}
                        benchmarkMetrics={benchmarks.metrics}
                      />
                    ))}
                    {sortedDevelopers.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={benchmarks.metric_info.length + 2} className="text-center text-muted-foreground py-8">
                          No developer data available.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          {/* Team Comparison */}
          {benchmarks.team_comparison && benchmarks.team_comparison.length >= 2 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Team Comparison (medians)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Team</TableHead>
                        <TableHead className="text-right">Developers</TableHead>
                        {benchmarks.metric_info.map((info) => (
                          <TableHead key={info.key} className="text-right">{info.label}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {benchmarks.team_comparison.map((t) => (
                        <TableRow key={t.team}>
                          <TableCell className="font-medium">{t.team}</TableCell>
                          <TableCell className="text-right">{t.sample_size}</TableCell>
                          {benchmarks.metric_info.map((info) => (
                            <TableCell key={info.key} className="text-right font-mono text-sm">
                              {formatMetricValue(t.metrics[info.key] ?? null, info)}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}

function DeveloperRow({
  dev,
  metricInfoList,
  benchmarkMetrics,
}: {
  dev: DeveloperBenchmarkRow
  metricInfoList: BenchmarkMetricInfo[]
  benchmarkMetrics: Record<string, BenchmarkMetric>
}) {
  return (
    <TableRow>
      <TableCell className="sticky left-0 bg-background">
        <Link
          to={`/team/${dev.developer_id}`}
          className="font-medium text-primary hover:underline"
        >
          {dev.display_name}
        </Link>
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">{dev.team || '\u2014'}</TableCell>
      {metricInfoList.map((info) => {
        const mv = dev.metrics[info.key]
        const band = mv?.percentile_band as Band | null
        const style = band ? bandStyles[band] : null
        const bm = benchmarkMetrics[info.key]
        // Bar width proportional to p75*1.5
        const maxVal = bm ? bm.p75 * 1.5 || 1 : 1
        const barWidth = mv?.value != null ? Math.min((mv.value / maxVal) * 100, 100) : 0

        return (
          <TableCell key={info.key} className="text-right">
            <div className="flex items-center justify-end gap-2">
              <div className="hidden w-16 sm:block">
                <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className={cn('h-full rounded-full', style?.bar || 'bg-muted-foreground/30')}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
              </div>
              <span className="w-14 font-mono text-sm">
                {formatMetricValue(mv?.value ?? null, info)}
              </span>
              {band && style && (
                <Badge variant="secondary" className={cn('w-20 justify-center text-[10px]', style.color)}>
                  {style.label}
                </Badge>
              )}
            </div>
          </TableCell>
        )
      })}
    </TableRow>
  )
}
