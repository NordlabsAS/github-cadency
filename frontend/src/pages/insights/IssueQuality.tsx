import { useMemo, useState } from 'react'
import { useDateRange } from '@/hooks/useDateRange'
import { useIssueCreatorStats } from '@/hooks/useStats'
import { useDevelopers } from '@/hooks/useDevelopers'
import StatCard from '@/components/StatCard'
import StatCardSkeleton from '@/components/StatCardSkeleton'
import TableSkeleton from '@/components/TableSkeleton'
import ErrorCard from '@/components/ErrorCard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { HelpCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { IssueCreatorStats } from '@/utils/types'

const MIN_ISSUES_DEFAULT = 5

// Column tooltip descriptions
const columnTooltips: Record<string, string> = {
  creator: 'GitHub user who created the issues. Sorted by volume — top creators are most relevant.',
  issues: 'Total issues created in the selected period.',
  checklist: 'Percentage of issues containing markdown checklists (- [ ] pattern), indicating structured acceptance criteria.',
  closeTime: 'Average hours from issue creation to close. Long times may indicate unclear requirements.',
  reopened: 'Percentage of issues reopened at least once. High reopens suggest incomplete definitions.',
  notPlanned: 'Percentage of closed issues marked "won\'t fix" or "not planned". High values suggest poor triage.',
  prsPerIssue: 'Average PRs linked to each issue via closing keywords. >1 may indicate scope too large.',
  timeToFirstPR: 'Average hours from issue creation to first linked PR. Long waits may mean unclear requirements.',
  commentBeforePR: 'Average discussion comments before the first PR is opened. High counts suggest ambiguous specs.',
  poorBody: 'Issues with descriptions under 100 characters — likely under-specified.',
}

function fmt(v: number | null, suffix = '', decimals = 1): string {
  if (v === null || v === undefined) return '—'
  return `${v.toFixed(decimals)}${suffix}`
}

function isWorse(value: number | null, avg: number | null, factor: number, higherIsWorse: boolean): boolean {
  if (value === null || avg === null || avg === 0) return false
  return higherIsWorse ? value > avg * factor : value < avg / factor
}

export default function IssueQuality() {
  const { dateFrom, dateTo } = useDateRange()
  const [teamFilter, setTeamFilter] = useState<string>('')
  const [minIssues, setMinIssues] = useState(MIN_ISSUES_DEFAULT)

  const { data, isLoading, isError, refetch } = useIssueCreatorStats(
    teamFilter || undefined,
    dateFrom,
    dateTo,
  )
  const { data: developers } = useDevelopers()

  const teams = useMemo(() => {
    if (!developers) return []
    const set = new Set<string>()
    for (const d of developers) {
      if (d.team) set.add(d.team)
    }
    return Array.from(set).sort()
  }, [developers])

  // Filter creators by minimum issue count
  const filteredCreators = useMemo(() => {
    if (!data) return []
    return data.creators.filter((c) => c.issues_created >= minIssues)
  }, [data, minIssues])

  if (isError) {
    return <ErrorCard message="Could not load issue creator analytics." onRetry={refetch} />
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Issue Quality</h1>
        <div className="grid gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
        <TableSkeleton columns={8} rows={5} />
      </div>
    )
  }

  const avg = data?.team_averages
  const totalCreators = data?.creators.length ?? 0

  if (!data || totalCreators === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Issue Quality</h1>
        <p className="text-muted-foreground">No issue data available for this period.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with filters */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Issue Quality</h1>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            Min issues
            <input
              type="number"
              min={1}
              max={100}
              value={minIssues}
              onChange={(e) => setMinIssues(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-16 rounded-md border bg-background px-2 py-1 text-sm"
            />
          </label>
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
      </div>

      {/* Summary stat cards — team averages */}
      <div className="grid gap-4 sm:grid-cols-4">
        <StatCard
          title="Active Creators"
          value={`${filteredCreators.length} / ${totalCreators}`}
          subtitle={`With ${minIssues}+ issues`}
          tooltip="Number of users meeting the minimum issue threshold vs total creators in the period."
        />
        <StatCard
          title="Avg Checklist %"
          value={fmt(avg?.pct_with_checklist, '%')}
          tooltip="Team average percentage of issues with acceptance criteria checklists."
        />
        <StatCard
          title="Avg Close Time"
          value={fmt(avg?.avg_time_to_close_hours, 'h')}
          tooltip="Team average hours from issue creation to close."
        />
        <StatCard
          title="Avg Reopen Rate"
          value={fmt(avg?.pct_reopened, '%')}
          tooltip="Team average percentage of issues reopened at least once."
        />
      </div>

      {/* Creator table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5 text-base">
            Per-Creator Breakdown
            <Tooltip>
              <TooltipTrigger className="inline-flex text-muted-foreground/60 hover:text-muted-foreground transition-colors">
                <HelpCircle className="h-3.5 w-3.5" />
              </TooltipTrigger>
              <TooltipContent>
                Red badges highlight metrics &gt;1.5x worse than team average. Helps identify creators whose issue definitions may cause friction.
              </TooltipContent>
            </Tooltip>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filteredCreators.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No creators with {minIssues}+ issues in this period. Try lowering the minimum.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <ColHeader label="Creator" tooltip={columnTooltips.creator} />
                    <ColHeader label="Issues" tooltip={columnTooltips.issues} align="right" />
                    <ColHeader label="Checklist %" tooltip={columnTooltips.checklist} align="right" />
                    <ColHeader label="Avg Close (h)" tooltip={columnTooltips.closeTime} align="right" />
                    <ColHeader label="Reopened %" tooltip={columnTooltips.reopened} align="right" />
                    <ColHeader label="Not Planned %" tooltip={columnTooltips.notPlanned} align="right" />
                    <ColHeader label="PRs/Issue" tooltip={columnTooltips.prsPerIssue} align="right" />
                    <ColHeader label="Time to PR (h)" tooltip={columnTooltips.timeToFirstPR} align="right" />
                    <ColHeader label="Comments Before PR" tooltip={columnTooltips.commentBeforePR} align="right" />
                    <ColHeader label="Poor Body" tooltip={columnTooltips.poorBody} align="right" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredCreators.map((c) => (
                    <CreatorRow key={c.github_username} creator={c} avg={avg!} />
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function ColHeader({ label, tooltip, align }: { label: string; tooltip: string; align?: 'right' }) {
  return (
    <TableHead className={cn(align === 'right' && 'text-right')}>
      <span className="inline-flex items-center gap-1">
        {label}
        <Tooltip>
          <TooltipTrigger className="inline-flex text-muted-foreground/60 hover:text-muted-foreground transition-colors">
            <HelpCircle className="h-3 w-3" />
          </TooltipTrigger>
          <TooltipContent className="max-w-xs">{tooltip}</TooltipContent>
        </Tooltip>
      </span>
    </TableHead>
  )
}

function CreatorRow({ creator: c, avg }: { creator: IssueCreatorStats; avg: IssueCreatorStats }) {
  return (
    <TableRow>
      <TableCell>
        <div className="flex flex-col">
          <span className="font-medium">{c.display_name ?? c.github_username}</span>
          {c.display_name && (
            <span className="text-xs text-muted-foreground">@{c.github_username}</span>
          )}
          {(c.team || c.role) && (
            <span className="text-xs text-muted-foreground">
              {[c.role, c.team].filter(Boolean).join(' · ')}
            </span>
          )}
        </div>
      </TableCell>
      <TableCell className="text-right font-medium">{c.issues_created}</TableCell>
      <MetricCell
        value={c.pct_with_checklist}
        avg={avg.pct_with_checklist}
        suffix="%"
        higherIsWorse={false}
      />
      <MetricCell
        value={c.avg_time_to_close_hours}
        avg={avg.avg_time_to_close_hours}
        suffix=""
        higherIsWorse={true}
      />
      <MetricCell
        value={c.pct_reopened}
        avg={avg.pct_reopened}
        suffix="%"
        higherIsWorse={true}
      />
      <MetricCell
        value={c.pct_closed_not_planned}
        avg={avg.pct_closed_not_planned}
        suffix="%"
        higherIsWorse={true}
      />
      <MetricCell
        value={c.avg_prs_per_issue}
        avg={avg.avg_prs_per_issue}
        suffix=""
        higherIsWorse={true}
      />
      <MetricCell
        value={c.avg_time_to_first_pr_hours}
        avg={avg.avg_time_to_first_pr_hours}
        suffix=""
        higherIsWorse={true}
      />
      <MetricCell
        value={c.avg_comment_count_before_pr}
        avg={avg.avg_comment_count_before_pr}
        suffix=""
        higherIsWorse={true}
      />
      <MetricCell
        value={c.issues_with_body_under_100_chars}
        avg={avg.issues_with_body_under_100_chars}
        suffix=""
        decimals={0}
        higherIsWorse={true}
      />
    </TableRow>
  )
}

function MetricCell({
  value,
  avg,
  suffix,
  higherIsWorse,
  decimals = 1,
}: {
  value: number | null
  avg: number | null
  suffix: string
  higherIsWorse: boolean
  decimals?: number
}) {
  const bad = isWorse(value, avg, 1.5, higherIsWorse)
  return (
    <TableCell className="text-right">
      <span className={cn(bad && 'inline-flex items-center')}>
        {fmt(value, suffix, decimals)}
        {bad && (
          <Badge variant="destructive" className="ml-1.5 text-[10px] px-1 py-0">
            !
          </Badge>
        )}
      </span>
    </TableCell>
  )
}
