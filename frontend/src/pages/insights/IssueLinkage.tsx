import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useDateRange } from '@/hooks/useDateRange'
import { useIssueLinkageByDeveloper } from '@/hooks/useStats'
import { useDevelopers } from '@/hooks/useDevelopers'
import StatCard from '@/components/StatCard'
import StatCardSkeleton from '@/components/StatCardSkeleton'
import TableSkeleton from '@/components/TableSkeleton'
import ErrorCard from '@/components/ErrorCard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import SortableHead from '@/components/SortableHead'
import type { DeveloperLinkageRow } from '@/utils/types'

type SortKey = 'name' | 'team' | 'prs_total' | 'prs_linked' | 'linkage_rate'

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`
}

export default function IssueLinkage() {
  const { dateFrom, dateTo } = useDateRange()
  const [teamFilter, setTeamFilter] = useState<string>('')
  const [sortKey, setSortKey] = useState<SortKey>('linkage_rate')
  const [sortAsc, setSortAsc] = useState(true)

  const { data, isLoading, isError, refetch } = useIssueLinkageByDeveloper(
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

  const sorted = useMemo(() => {
    if (!data) return []
    const rows = [...data.developers]
    rows.sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'name': cmp = (a.display_name).localeCompare(b.display_name); break
        case 'team': cmp = (a.team ?? '').localeCompare(b.team ?? ''); break
        case 'prs_total': cmp = a.prs_total - b.prs_total; break
        case 'prs_linked': cmp = a.prs_linked - b.prs_linked; break
        case 'linkage_rate': cmp = a.linkage_rate - b.linkage_rate; break
      }
      return sortAsc ? cmp : -cmp
    })
    return rows
  }, [data, sortKey, sortAsc])

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc((v) => !v)
    } else {
      setSortKey(key)
      // Default ascending for text columns, descending for numeric columns
      setSortAsc(key === 'name' || key === 'team' || key === 'linkage_rate')
    }
  }

  if (isError) {
    return <ErrorCard message="Could not load issue linkage data." onRetry={refetch} />
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Issue Linkage</h1>
        <div className="grid gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
        <TableSkeleton columns={5} rows={5} />
      </div>
    )
  }

  if (!data || data.developers.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Issue Linkage</h1>
        <p className="text-muted-foreground">No PR data available for this period.</p>
      </div>
    )
  }

  const totalPRs = data.developers.reduce((s, d) => s + d.prs_total, 0)
  const totalLinked = data.developers.reduce((s, d) => s + d.prs_linked, 0)

  return (
    <div className="space-y-6">
      {/* Header with filter */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Issue Linkage</h1>
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

      {/* Summary stat cards */}
      <div className="grid gap-4 sm:grid-cols-4">
        <StatCard
          title="Total PRs"
          value={totalPRs}
          tooltip="Total pull requests opened by all developers in this period."
        />
        <StatCard
          title="PRs Linked to Issues"
          value={totalLinked}
          subtitle={pct(totalPRs > 0 ? totalLinked / totalPRs : 0)}
          tooltip="PRs containing closing keywords (Closes/Fixes/Resolves #N) linking them to issues."
        />
        <StatCard
          title="Team Avg Linkage"
          value={pct(data.team_average_rate)}
          tooltip="Average issue linkage rate across all developers with at least 1 PR."
        />
        <StatCard
          title="Needs Attention"
          value={data.attention_developers.length}
          subtitle={`Below ${pct(data.attention_threshold)}`}
          tooltip={`Developers with less than ${pct(data.attention_threshold)} of their PRs linked to issues.`}
        />
      </div>

      {/* Attention needed callout */}
      {data.attention_developers.length > 0 && (
        <Card className="border-amber-500/50 bg-amber-500/5">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base text-amber-600 dark:text-amber-400">
              <AlertTriangle className="h-4 w-4" />
              Attention Needed — Low Issue Linkage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-3 text-sm text-muted-foreground">
              These developers have less than {pct(data.attention_threshold)} of their PRs linked to issues.
              Consider discussing PR workflow practices with them.
            </p>
            <div className="flex flex-wrap gap-2">
              {data.attention_developers.map((d) => (
                <Link
                  key={d.developer_id}
                  to={`/team/${d.developer_id}`}
                  className="inline-flex items-center gap-1.5 rounded-md border border-amber-500/30 bg-amber-500/10 px-2.5 py-1.5 text-sm transition-colors hover:bg-amber-500/20"
                >
                  <span className="font-medium">{d.display_name}</span>
                  <Badge variant="outline" className="text-[10px] px-1 py-0 border-amber-500/40">
                    {pct(d.linkage_rate)}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    ({d.prs_linked}/{d.prs_total} PRs)
                  </span>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Developer table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Per-Developer Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableHead field="name" current={sortKey} asc={sortAsc} onToggle={handleSort}>Developer</SortableHead>
                  <SortableHead field="team" current={sortKey} asc={sortAsc} onToggle={handleSort}>Team</SortableHead>
                  <SortableHead field="prs_total" current={sortKey} asc={sortAsc} onToggle={handleSort}>Total PRs</SortableHead>
                  <SortableHead field="prs_linked" current={sortKey} asc={sortAsc} onToggle={handleSort}>Linked PRs</SortableHead>
                  <SortableHead field="linkage_rate" current={sortKey} asc={sortAsc} onToggle={handleSort}>Linkage Rate</SortableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((d) => (
                  <LinkageRow key={d.developer_id} row={d} threshold={data.attention_threshold} />
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function LinkageRow({ row: d, threshold }: { row: DeveloperLinkageRow; threshold: number }) {
  const belowThreshold = d.linkage_rate < threshold
  return (
    <TableRow className={cn(belowThreshold && 'bg-amber-500/5')}>
      <TableCell className="px-2">
        <Link to={`/team/${d.developer_id}`} className="hover:underline">
          <div className="flex flex-col">
            <span className="font-medium">{d.display_name}</span>
            <span className="text-xs text-muted-foreground">@{d.github_username}</span>
          </div>
        </Link>
      </TableCell>
      <TableCell className="px-2 text-sm text-muted-foreground">
        {d.team ?? '—'}
      </TableCell>
      <TableCell className="text-right px-2">{d.prs_total}</TableCell>
      <TableCell className="text-right px-2">{d.prs_linked}</TableCell>
      <TableCell className="text-right px-2">
        <span className="inline-flex items-center gap-1.5">
          <RateBar rate={d.linkage_rate} belowThreshold={belowThreshold} />
          <span className={cn('font-medium', belowThreshold && 'text-amber-600 dark:text-amber-400')}>
            {pct(d.linkage_rate)}
          </span>
        </span>
      </TableCell>
    </TableRow>
  )
}

function RateBar({ rate, belowThreshold }: { rate: number; belowThreshold: boolean }) {
  return (
    <div className="hidden sm:block w-16 h-2 rounded-full bg-muted overflow-hidden">
      <div
        className={cn(
          'h-full rounded-full transition-all',
          belowThreshold ? 'bg-amber-500' : 'bg-emerald-500',
        )}
        style={{ width: `${Math.min(rate * 100, 100)}%` }}
      />
    </div>
  )
}
