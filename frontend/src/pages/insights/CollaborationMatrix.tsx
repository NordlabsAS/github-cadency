import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDateRange } from '@/hooks/useDateRange'
import { useCollaboration } from '@/hooks/useStats'
import { useDevelopers } from '@/hooks/useDevelopers'
import ErrorCard from '@/components/ErrorCard'
import PairDetailSheet from '@/components/PairDetailSheet'
import SortableHead from '@/components/SortableHead'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
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
import type { CollaborationPair, CollaborationInsights } from '@/utils/types'

const PAGE_SIZE = 25

export default function CollaborationMatrix() {
  const { dateFrom, dateTo } = useDateRange()
  const navigate = useNavigate()
  const [teamFilter, setTeamFilter] = useState<string>('')
  const [selectedPair, setSelectedPair] = useState<{ reviewerId: number; authorId: number } | null>(null)
  const [activeTeamPair, setActiveTeamPair] = useState<{ reviewerTeam: string; authorTeam: string } | null>(null)
  const [sortField, setSortField] = useState<SortField>('reviews_count')
  const [sortAsc, setSortAsc] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading, isError, refetch } = useCollaboration(teamFilter || undefined, dateFrom, dateTo)
  const { data: developers } = useDevelopers()

  const teams = useMemo(() => {
    if (!developers) return []
    const set = new Set(developers.map((d) => d.team).filter(Boolean) as string[])
    return Array.from(set).sort()
  }, [developers])

  function handleSortToggle(field: SortField) {
    if (field === sortField) {
      setSortAsc(!sortAsc)
    } else {
      setSortField(field)
      setSortAsc(field === 'reviewer_name' || field === 'author_name')
    }
    setCurrentPage(1)
  }

  function handleTeamCellClick(reviewerTeam: string, authorTeam: string) {
    if (activeTeamPair?.reviewerTeam === reviewerTeam && activeTeamPair?.authorTeam === authorTeam) {
      setActiveTeamPair(null)
    } else {
      setActiveTeamPair({ reviewerTeam, authorTeam })
    }
    setCurrentPage(1)
  }

  if (isError) {
    return <ErrorCard message="Could not load collaboration data." onRetry={refetch} />
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Collaboration Matrix</h1>
        <Skeleton className="h-48 w-full rounded-lg" />
        <Skeleton className="h-64 w-full rounded-lg" />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-lg" />)}
        </div>
      </div>
    )
  }

  if (!data || data.matrix.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Collaboration Matrix</h1>
        <p className="text-muted-foreground">No review data available for this period.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Collaboration Matrix</h1>
        {teams.length > 0 && (
          <select
            value={teamFilter}
            onChange={(e) => { setTeamFilter(e.target.value); setActiveTeamPair(null); setCurrentPage(1) }}
            className="rounded-md border bg-background px-2 py-1 text-sm"
          >
            <option value="">All teams</option>
            {teams.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        )}
      </div>

      <TeamHeatmap
        matrix={data.matrix}
        activeFilter={activeTeamPair}
        onCellClick={handleTeamCellClick}
      />

      <PairsTable
        matrix={data.matrix}
        teamFilter={activeTeamPair}
        sortField={sortField}
        sortAsc={sortAsc}
        currentPage={currentPage}
        searchQuery={searchQuery}
        onSortToggle={handleSortToggle}
        onPageChange={setCurrentPage}
        onSearchChange={(q) => { setSearchQuery(q); setCurrentPage(1) }}
        onPairClick={(reviewerId, authorId) => setSelectedPair({ reviewerId, authorId })}
        onPairNavigate={(reviewerId, authorId) => navigate(`/insights/collaboration/${reviewerId}/${authorId}`)}
      />

      <InsightsPanel insights={data.insights} />

      <PairDetailSheet
        reviewerId={selectedPair?.reviewerId ?? null}
        authorId={selectedPair?.authorId ?? null}
        open={selectedPair !== null}
        onOpenChange={(open) => { if (!open) setSelectedPair(null) }}
      />
    </div>
  )
}

// --- Team Heatmap ---

interface TeamAggregation {
  total: number
  approvals: number
  changes_requested: number
}

function TeamHeatmap({
  matrix,
  activeFilter,
  onCellClick,
}: {
  matrix: CollaborationPair[]
  activeFilter: { reviewerTeam: string; authorTeam: string } | null
  onCellClick: (reviewerTeam: string, authorTeam: string) => void
}) {
  const { teamNames, cellMap, maxCount } = useMemo(() => {
    const map = new Map<string, TeamAggregation>()
    const teamSet = new Set<string>()

    for (const pair of matrix) {
      const rTeam = pair.reviewer_team ?? 'Unassigned'
      const aTeam = pair.author_team ?? 'Unassigned'
      teamSet.add(rTeam)
      teamSet.add(aTeam)
      const key = `${rTeam}::${aTeam}`
      const existing = map.get(key)
      if (existing) {
        existing.total += pair.reviews_count
        existing.approvals += pair.approvals
        existing.changes_requested += pair.changes_requested
      } else {
        map.set(key, {
          total: pair.reviews_count,
          approvals: pair.approvals,
          changes_requested: pair.changes_requested,
        })
      }
    }

    let max = 0
    for (const v of map.values()) {
      if (v.total > max) max = v.total
    }

    const names = Array.from(teamSet).sort((a, b) => {
      if (a === 'Unassigned') return 1
      if (b === 'Unassigned') return -1
      return a.localeCompare(b)
    })

    return { teamNames: names, cellMap: map, maxCount: max }
  }, [matrix])

  if (teamNames.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Team Review Flow</CardTitle>
        <p className="text-xs text-muted-foreground">
          Rows = reviewing teams, Columns = PR author teams. Click a cell to filter the pairs table below.
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <div
            className="inline-grid gap-1"
            style={{
              gridTemplateColumns: `140px repeat(${teamNames.length}, minmax(80px, 120px))`,
            }}
          >
            {/* Header row */}
            <div />
            {teamNames.map((t) => (
              <div
                key={`h-${t}`}
                className="truncate px-2 py-1.5 text-center text-xs font-medium text-muted-foreground"
                title={t}
              >
                {t}
              </div>
            ))}

            {/* Data rows */}
            {teamNames.map((rTeam) => (
              <>
                <div
                  key={`label-${rTeam}`}
                  className="truncate pr-2 py-1.5 text-right text-xs font-medium text-muted-foreground"
                  title={rTeam}
                >
                  {rTeam}
                </div>
                {teamNames.map((aTeam) => {
                  const cell = cellMap.get(`${rTeam}::${aTeam}`)
                  const count = cell?.total ?? 0
                  const intensity = maxCount > 0 ? count / maxCount : 0
                  const isActive = activeFilter?.reviewerTeam === rTeam && activeFilter?.authorTeam === aTeam

                  return (
                    <div
                      key={`c-${rTeam}-${aTeam}`}
                      className={cn(
                        'flex flex-col items-center justify-center rounded-md text-xs font-medium transition-all cursor-pointer',
                        'hover:ring-2 hover:ring-primary/50',
                        isActive && 'ring-2 ring-primary',
                        count === 0 && 'hover:ring-1 hover:ring-foreground/20'
                      )}
                      style={{
                        backgroundColor: count > 0
                          ? `hsl(var(--primary) / ${0.08 + intensity * 0.72})`
                          : undefined,
                        minHeight: '48px',
                      }}
                      onClick={() => onCellClick(rTeam, aTeam)}
                      title={`${rTeam} reviewing ${aTeam}: ${count} reviews${cell ? ` (${cell.approvals} approved, ${cell.changes_requested} changes requested)` : ''}`}
                    >
                      {count > 0 ? (
                        <span className={cn(
                          intensity > 0.5 ? 'text-primary-foreground' : 'text-foreground'
                        )}>
                          {count}
                        </span>
                      ) : (
                        <span className="text-muted-foreground/30">0</span>
                      )}
                    </div>
                  )
                })}
              </>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// --- Pairs Table ---

type SortField = 'reviewer_name' | 'author_name' | 'reviews_count' | 'approvals' | 'changes_requested'

function PairsTable({
  matrix,
  teamFilter,
  sortField,
  sortAsc,
  currentPage,
  searchQuery,
  onSortToggle,
  onPageChange,
  onSearchChange,
  onPairClick,
  onPairNavigate,
}: {
  matrix: CollaborationPair[]
  teamFilter: { reviewerTeam: string; authorTeam: string } | null
  sortField: SortField
  sortAsc: boolean
  currentPage: number
  searchQuery: string
  onSortToggle: (field: SortField) => void
  onPageChange: (page: number) => void
  onSearchChange: (query: string) => void
  onPairClick: (reviewerId: number, authorId: number) => void
  onPairNavigate: (reviewerId: number, authorId: number) => void
}) {
  const { rows, totalCount, totalPages } = useMemo(() => {
    let filtered = matrix

    // Team pair filter from heatmap
    if (teamFilter) {
      filtered = filtered.filter((p) => {
        const rTeam = p.reviewer_team ?? 'Unassigned'
        const aTeam = p.author_team ?? 'Unassigned'
        return rTeam === teamFilter.reviewerTeam && aTeam === teamFilter.authorTeam
      })
    }

    // Text search
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      filtered = filtered.filter(
        (p) => p.reviewer_name.toLowerCase().includes(q) || p.author_name.toLowerCase().includes(q)
      )
    }

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      let cmp = 0
      switch (sortField) {
        case 'reviewer_name':
          cmp = a.reviewer_name.localeCompare(b.reviewer_name)
          break
        case 'author_name':
          cmp = a.author_name.localeCompare(b.author_name)
          break
        case 'reviews_count':
          cmp = a.reviews_count - b.reviews_count
          break
        case 'approvals':
          cmp = a.approvals - b.approvals
          break
        case 'changes_requested':
          cmp = a.changes_requested - b.changes_requested
          break
      }
      return sortAsc ? cmp : -cmp
    })

    const total = sorted.length
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))
    const start = (currentPage - 1) * PAGE_SIZE
    const pageRows = sorted.slice(start, start + PAGE_SIZE)

    return { rows: pageRows, totalCount: total, totalPages: pages }
  }, [matrix, teamFilter, searchQuery, sortField, sortAsc, currentPage])

  const startIdx = (currentPage - 1) * PAGE_SIZE + 1
  const endIdx = Math.min(currentPage * PAGE_SIZE, totalCount)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Review Pairs</CardTitle>
            <p className="text-xs text-muted-foreground">
              All reviewer-author pairs.{' '}
              {teamFilter && (
                <button
                  type="button"
                  className="text-primary hover:underline"
                  onClick={() => onSearchChange('')}
                >
                  Filtered by {teamFilter.reviewerTeam} → {teamFilter.authorTeam}
                </button>
              )}
            </p>
          </div>
          <Input
            placeholder="Search by name..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="max-w-xs text-sm"
          />
        </div>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">No pairs match the current filters.</p>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableHead field="reviewer_name" current={sortField} asc={sortAsc} onToggle={onSortToggle}>
                    Reviewer
                  </SortableHead>
                  <SortableHead field="author_name" current={sortField} asc={sortAsc} onToggle={onSortToggle}>
                    Author
                  </SortableHead>
                  <SortableHead field="reviews_count" current={sortField} asc={sortAsc} onToggle={onSortToggle}>
                    Reviews
                  </SortableHead>
                  <SortableHead field="approvals" current={sortField} asc={sortAsc} onToggle={onSortToggle}>
                    Approvals
                  </SortableHead>
                  <SortableHead field="changes_requested" current={sortField} asc={sortAsc} onToggle={onSortToggle}>
                    Changes Req'd
                  </SortableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((pair) => (
                  <TableRow key={`${pair.reviewer_id}-${pair.author_id}`}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{pair.reviewer_name}</span>
                        {pair.reviewer_team && (
                          <Badge variant="outline" className="text-[10px] px-1 py-0">{pair.reviewer_team}</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{pair.author_name}</span>
                        {pair.author_team && (
                          <Badge variant="outline" className="text-[10px] px-1 py-0">{pair.author_team}</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <button
                        type="button"
                        className="text-primary hover:underline font-medium"
                        onClick={() => onPairClick(pair.reviewer_id, pair.author_id)}
                      >
                        {pair.reviews_count}
                      </button>
                    </TableCell>
                    <TableCell>{pair.approvals}</TableCell>
                    <TableCell>{pair.changes_requested}</TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs"
                        onClick={() => onPairNavigate(pair.reviewer_id, pair.author_id)}
                      >
                        Detail &rarr;
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4 text-sm text-muted-foreground">
                <span>
                  Showing {startIdx}–{endIdx} of {totalCount} pairs
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage <= 1}
                    onClick={() => onPageChange(currentPage - 1)}
                  >
                    Previous
                  </Button>
                  <span>
                    Page {currentPage} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage >= totalPages}
                    onClick={() => onPageChange(currentPage + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

// --- Insights Panel (Bus Factors, Silos, Isolated Developers) ---

function InsightsPanel({ insights }: { insights: CollaborationInsights }) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {/* Bus Factors */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Bus Factors</CardTitle>
          <p className="text-xs text-muted-foreground">Repos where one reviewer handles {'>'}70% of reviews</p>
        </CardHeader>
        <CardContent>
          {insights.bus_factors.length === 0 ? (
            <p className="text-sm text-muted-foreground">No bus factors detected.</p>
          ) : (
            <ul className="space-y-2">
              {insights.bus_factors.map((bf) => (
                <li key={`${bf.repo_name}-${bf.sole_reviewer_id}`} className="flex items-center justify-between text-sm">
                  <span>
                    <span className="font-medium">{bf.sole_reviewer_name}</span>
                    <span className="text-muted-foreground"> in {bf.repo_name}</span>
                  </span>
                  <Badge variant="secondary" className="bg-red-500/10 text-red-600">
                    {bf.review_share_pct.toFixed(0)}%
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Silos */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Team Silos</CardTitle>
          <p className="text-xs text-muted-foreground">Team pairs with zero cross-team reviews</p>
        </CardHeader>
        <CardContent>
          {insights.silos.length === 0 ? (
            <p className="text-sm text-emerald-600">No silos detected — all teams collaborate.</p>
          ) : (
            <ul className="space-y-2">
              {insights.silos.map((silo, i) => (
                <li key={i} className="text-sm">
                  <span className="font-medium">{silo.team_a}</span>
                  <span className="text-muted-foreground"> ↔ </span>
                  <span className="font-medium">{silo.team_b}</span>
                  {silo.note && (
                    <span className="ml-1 text-xs text-muted-foreground">— {silo.note}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Isolated Developers */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Isolated Developers</CardTitle>
          <p className="text-xs text-muted-foreground">Developers with minimal review interaction</p>
        </CardHeader>
        <CardContent>
          {insights.isolated_developers.length === 0 ? (
            <p className="text-sm text-emerald-600">No isolated developers.</p>
          ) : (
            <ul className="space-y-1">
              {insights.isolated_developers.map((dev) => (
                <li key={dev.developer_id} className="text-sm">
                  <Link to={`/team/${dev.developer_id}`} className="text-primary hover:underline">
                    {dev.display_name}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
