import { useMemo, useState } from 'react'
import { useDateRange } from '@/hooks/useDateRange'
import { useCodeChurn } from '@/hooks/useStats'
import { useRepos } from '@/hooks/useSync'
import StatCard from '@/components/StatCard'
import StatCardSkeleton from '@/components/StatCardSkeleton'
import TableSkeleton from '@/components/TableSkeleton'
import ErrorCard from '@/components/ErrorCard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { HelpCircle, Flame, FolderX, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

function formatDate(iso: string | null): string {
  if (!iso) return 'Never'
  return new Date(iso).toLocaleDateString()
}

function churnLevel(frequency: number): { label: string; color: string } {
  if (frequency >= 10) return { label: 'Critical', color: 'text-red-600 dark:text-red-400' }
  if (frequency >= 5) return { label: 'High', color: 'text-orange-600 dark:text-orange-400' }
  if (frequency >= 3) return { label: 'Medium', color: 'text-yellow-600 dark:text-yellow-400' }
  return { label: 'Low', color: 'text-muted-foreground' }
}

export default function CodeChurn() {
  const { dateFrom, dateTo } = useDateRange()
  const { data: repos } = useRepos()
  const [selectedRepoId, setSelectedRepoId] = useState<number | null>(null)

  const trackedRepos = useMemo(
    () => (repos ?? []).filter((r) => r.is_tracked),
    [repos],
  )

  // Auto-select first repo if none selected
  const effectiveRepoId = selectedRepoId ?? trackedRepos[0]?.id ?? null

  const { data, isLoading, isError, refetch } = useCodeChurn(
    effectiveRepoId,
    dateFrom,
    dateTo,
  )

  const coveragePct = data && data.total_files_in_repo > 0
    ? ((data.total_files_changed / data.total_files_in_repo) * 100).toFixed(1)
    : null

  if (!isLoading && trackedRepos.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Code Churn</h1>
        <ErrorCard message="No tracked repositories found. Enable tracking on the Repos page." />
      </div>
    )
  }

  if (isError) {
    return <ErrorCard message="Could not load code churn data." onRetry={refetch} />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Code Churn</h1>
        <select
          className="rounded-md border bg-background px-3 py-1.5 text-sm"
          value={effectiveRepoId ?? ''}
          onChange={(e) => setSelectedRepoId(Number(e.target.value) || null)}
        >
          {trackedRepos.length === 0 && <option value="">No repos</option>}
          {trackedRepos.map((r) => (
            <option key={r.id} value={r.id}>
              {r.full_name || r.name}
            </option>
          ))}
        </select>
      </div>

      {/* Summary cards */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
      ) : data ? (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            title="Files in Repo"
            value={data.total_files_in_repo.toLocaleString()}
            tooltip="Total files tracked in the repository's default branch via GitHub Trees API."
          />
          <StatCard
            title="Files Changed"
            value={data.total_files_changed.toLocaleString()}
            tooltip="Distinct files modified by PRs in the selected date range."
          />
          <StatCard
            title="Codebase Coverage"
            value={coveragePct ? `${coveragePct}%` : '—'}
            tooltip="Percentage of repo files touched by at least one PR in the period. Low coverage may indicate stale areas."
          />
        </div>
      ) : null}

      {data?.tree_truncated && (
        <div className="flex items-center gap-2 rounded-md border border-yellow-300 bg-yellow-50 px-4 py-2 text-sm text-yellow-800 dark:border-yellow-700 dark:bg-yellow-950 dark:text-yellow-200">
          <AlertTriangle className="h-4 w-4" />
          Repository tree was truncated by GitHub (over 100,000 entries). Stale directory data may be incomplete.
        </div>
      )}

      {/* Hotspot files */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Flame className="h-5 w-5 text-orange-500" />
            <CardTitle>Hotspot Files</CardTitle>
            <Tooltip>
              <TooltipTrigger>
                <HelpCircle className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                Files ranked by how many distinct PRs modified them in the period. High-churn files may need refactoring or indicate shared bottleneck code.
              </TooltipContent>
            </Tooltip>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton columns={6} rows={5} />
          ) : !data || data.hotspot_files.length === 0 ? (
            <p className="text-sm text-muted-foreground">No file changes found in this period.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>File Path</TableHead>
                  <TableHead className="text-right">PRs</TableHead>
                  <TableHead className="text-right">Additions</TableHead>
                  <TableHead className="text-right">Deletions</TableHead>
                  <TableHead className="text-right">Total Churn</TableHead>
                  <TableHead className="text-right">Contributors</TableHead>
                  <TableHead>Last Modified</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.hotspot_files.map((f) => {
                  const level = churnLevel(f.change_frequency)
                  return (
                    <TableRow key={f.path}>
                      <TableCell className="font-mono text-xs max-w-md truncate" title={f.path}>
                        {f.path}
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={cn('font-medium', level.color)}>
                          {f.change_frequency}
                        </span>
                      </TableCell>
                      <TableCell className="text-right text-green-600 dark:text-green-400">
                        +{f.total_additions}
                      </TableCell>
                      <TableCell className="text-right text-red-600 dark:text-red-400">
                        -{f.total_deletions}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {f.total_churn.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right">{f.contributor_count}</TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {formatDate(f.last_modified_at)}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Stale directories */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <FolderX className="h-5 w-5 text-amber-500" />
            <CardTitle>Stale Directories</CardTitle>
            <Tooltip>
              <TooltipTrigger>
                <HelpCircle className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                Top-level directories with zero PR activity in the selected period. These may contain abandoned or legacy code.
              </TooltipContent>
            </Tooltip>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton columns={3} rows={3} />
          ) : !data || data.stale_directories.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {data?.total_files_in_repo === 0
                ? 'No repo tree data available. Run a sync to populate.'
                : 'All directories have recent PR activity.'}
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Directory</TableHead>
                  <TableHead className="text-right">Files</TableHead>
                  <TableHead>Last PR Activity</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.stale_directories.map((d) => (
                  <TableRow key={d.path}>
                    <TableCell className="font-mono text-sm">
                      {d.path}/
                    </TableCell>
                    <TableCell className="text-right">{d.file_count}</TableCell>
                    <TableCell>
                      {d.last_pr_activity ? (
                        <span className="text-muted-foreground text-sm">
                          {formatDate(d.last_pr_activity)}
                        </span>
                      ) : (
                        <Badge variant="outline" className="text-amber-600 border-amber-300 dark:text-amber-400 dark:border-amber-700">
                          Never touched
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
