import { useMemo, useState, useId, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { useDateRange } from '@/hooks/useDateRange'
import { useWorkAllocation, useWorkAllocationItems } from '@/hooks/useStats'
import StatCard from '@/components/StatCard'
import StatCardSkeleton from '@/components/StatCardSkeleton'
import TableSkeleton from '@/components/TableSkeleton'
import ErrorCard from '@/components/ErrorCard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Switch } from '@/components/ui/switch'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from 'recharts'
import { HelpCircle, Sparkles, ArrowRight, GitPullRequest, CircleDot } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAISettings } from '@/hooks/useAISettings'
import type { WorkCategory } from '@/utils/types'
import { FALLBACK_CATEGORY_CONFIG, FALLBACK_CATEGORY_ORDER } from '@/utils/categoryConfig'
import { useCategoryConfig } from '@/hooks/useWorkCategories'

// --- Custom Tooltip for charts ---

function ChartTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number; payload: { color: string; pct: number } }> }) {
  if (!active || !payload?.length) return null
  const entry = payload[0]
  return (
    <div className="rounded-lg border bg-card px-3 py-2 shadow-md">
      <div className="flex items-center gap-2">
        <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: entry.payload.color }} />
        <span className="text-sm font-medium">{entry.name}</span>
      </div>
      <div className="mt-1 text-xs text-muted-foreground">
        {entry.value} items ({entry.payload.pct.toFixed(1)}%)
      </div>
    </div>
  )
}

function TrendTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) {
  if (!active || !payload?.length) return null
  const total = payload.reduce((s, p) => s + (p.value || 0), 0)
  return (
    <div className="rounded-lg border bg-card px-3 py-2.5 shadow-md min-w-[160px]">
      <div className="text-xs font-medium text-muted-foreground mb-1.5">{label}</div>
      {payload.filter(p => p.value > 0).map((p) => (
        <div key={p.name} className="flex items-center justify-between gap-3 text-xs py-0.5">
          <div className="flex items-center gap-1.5">
            <div className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
            <span>{p.name}</span>
          </div>
          <span className="font-medium tabular-nums">{p.value}</span>
        </div>
      ))}
      <div className="mt-1 pt-1 border-t text-xs font-medium flex justify-between">
        <span>Total</span>
        <span className="tabular-nums">{total}</span>
      </div>
    </div>
  )
}

// --- Category Preview (inline drill-down) ---

function CategoryPreview({
  category,
  itemType,
  dateFrom,
  dateTo,
}: {
  category: string
  itemType: 'pr' | 'issue'
  dateFrom?: string
  dateTo?: string
}) {
  const { data, isLoading } = useWorkAllocationItems(
    category,
    itemType,
    dateFrom,
    dateTo,
    1,
    5,
    true,
  )

  if (isLoading) {
    return <div className="mt-3 space-y-2">{[...Array(3)].map((_, i) => <div key={i} className="h-8 rounded bg-muted animate-pulse" />)}</div>
  }

  if (!data || data.total === 0) {
    return <p className="mt-3 text-xs text-muted-foreground">No items in this category.</p>
  }

  return (
    <div className="mt-3">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="h-7 text-xs">Item</TableHead>
            <TableHead className="h-7 text-xs">Repo</TableHead>
            <TableHead className="h-7 text-xs text-right">Date</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.items.map((item) => (
            <TableRow key={`${item.type}-${item.id}`} className="text-xs">
              <TableCell className="py-1.5">
                <div className="flex items-center gap-1.5">
                  {item.type === 'pr' ? (
                    <GitPullRequest className="h-3 w-3 text-muted-foreground shrink-0" />
                  ) : (
                    <CircleDot className="h-3 w-3 text-muted-foreground shrink-0" />
                  )}
                  {item.html_url ? (
                    <a
                      href={item.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline text-foreground truncate max-w-[280px]"
                    >
                      #{item.number} {item.title}
                    </a>
                  ) : (
                    <span className="truncate max-w-[280px]">#{item.number} {item.title}</span>
                  )}
                </div>
              </TableCell>
              <TableCell className="py-1.5 text-muted-foreground">{item.repo_name}</TableCell>
              <TableCell className="py-1.5 text-right text-muted-foreground tabular-nums">
                {(item.merged_at || item.created_at)
                  ? new Date(item.merged_at || item.created_at!).toLocaleDateString()
                  : '-'}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {data.total > 5 && (
        <Link
          to={`/insights/investment/${category}?type=${itemType}`}
          className="mt-2 flex items-center gap-1 text-xs text-primary hover:underline"
        >
          View all {data.total} items <ArrowRight className="h-3 w-3" />
        </Link>
      )}
      {data.total <= 5 && data.total > 0 && (
        <Link
          to={`/insights/investment/${category}?type=${itemType}`}
          className="mt-2 flex items-center gap-1 text-xs text-primary hover:underline"
        >
          Open detail view <ArrowRight className="h-3 w-3" />
        </Link>
      )}
    </div>
  )
}

// --- Clickable Legend ---

function CategoryLegend({
  data,
  selected,
  onSelect,
}: {
  data: { name: string; value: number; color: string; category: string }[]
  selected: string | null
  onSelect: (category: string | null) => void
}) {
  return (
    <div className="mt-3 flex flex-wrap justify-center gap-3">
      {data.map((d) => (
        <button
          key={d.name}
          onClick={() => onSelect(selected === d.category ? null : d.category)}
          className={cn(
            'flex items-center gap-1.5 text-xs rounded-full px-2 py-0.5 transition-colors cursor-pointer',
            selected === d.category
              ? 'bg-accent ring-1 ring-ring'
              : selected
                ? 'opacity-40'
                : 'hover:bg-accent/50',
          )}
        >
          <div className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
          <span className="text-muted-foreground">
            {d.name} ({d.value})
          </span>
        </button>
      ))}
    </div>
  )
}

// --- Main Page ---

export default function Investment() {
  const { dateFrom, dateTo } = useDateRange()
  const [useAi, setUseAi] = useState(false)
  const { data: aiSettings } = useAISettings()
  const { data, isLoading, isError, refetch } = useWorkAllocation(
    undefined,
    dateFrom,
    dateTo,
    useAi,
  )
  const pieId = useId()
  const catConfig = useCategoryConfig()
  const CATEGORY_CONFIG = catConfig?.config ?? FALLBACK_CATEGORY_CONFIG
  const CATEGORY_ORDER = catConfig?.order ?? FALLBACK_CATEGORY_ORDER
  const [selectedPrCategory, setSelectedPrCategory] = useState<string | null>(null)
  const [selectedIssueCategory, setSelectedIssueCategory] = useState<string | null>(null)

  const prDonutData = useMemo(() => {
    if (!data) return []
    return data.pr_allocation
      .filter((a) => a.count > 0)
      .map((a) => ({
        name: CATEGORY_CONFIG[a.category]?.label ?? a.category,
        value: a.count,
        color: CATEGORY_CONFIG[a.category]?.color ?? '#94a3b8',
        pct: a.pct_of_total,
        category: a.category,
      }))
  }, [data])

  const issueDonutData = useMemo(() => {
    if (!data) return []
    return data.issue_allocation
      .filter((a) => a.count > 0)
      .map((a) => ({
        name: CATEGORY_CONFIG[a.category]?.label ?? a.category,
        value: a.count,
        color: CATEGORY_CONFIG[a.category]?.color ?? '#94a3b8',
        pct: a.pct_of_total,
        category: a.category,
      }))
  }, [data])

  const trendData = useMemo(() => {
    if (!data) return []
    return data.trend.map((p) => ({
      label: p.period_label,
      ...Object.fromEntries(
        CATEGORY_ORDER.map((cat) => [cat, p.pr_categories[cat] ?? 0]),
      ),
    }))
  }, [data])

  const [sortKey, setSortKey] = useState<'total_prs' | 'total_issues' | WorkCategory>('total_prs')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const sortedDevs = useMemo(() => {
    if (!data) return []
    return [...data.developer_breakdown].sort((a, b) => {
      let va: number, vb: number
      if (sortKey === 'total_prs') {
        va = a.total_prs; vb = b.total_prs
      } else if (sortKey === 'total_issues') {
        va = a.total_issues; vb = b.total_issues
      } else {
        va = (a.pr_categories[sortKey] ?? 0); vb = (b.pr_categories[sortKey] ?? 0)
      }
      return sortDir === 'desc' ? vb - va : va - vb
    })
  }, [data, sortKey, sortDir])

  const toggleSort = useCallback((key: typeof sortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }, [sortKey])

  if (isError) {
    return <ErrorCard message="Failed to load work allocation data." onRetry={refetch} />
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Engineering Investment</h1>
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Card><CardContent className="h-[340px]" /></Card>
          <Card><CardContent className="h-[340px]" /></Card>
        </div>
        <Card><CardContent className="h-[300px]" /></Card>
        <TableSkeleton rows={5} columns={7} />
      </div>
    )
  }

  if (!data || (data.total_prs === 0 && data.total_issues === 0)) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Engineering Investment</h1>
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No merged PRs or issues found in this period.
          </CardContent>
        </Card>
      </div>
    )
  }

  const totalPrCount = prDonutData.reduce((s, d) => s + d.value, 0)
  const totalIssueCount = issueDonutData.reduce((s, d) => s + d.value, 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">Engineering Investment</h1>
          <Tooltip>
            <TooltipTrigger>
              <HelpCircle className="h-4 w-4 text-muted-foreground" />
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p>Classifies merged PRs and created issues into categories using GitHub labels, title keywords, and optionally AI. Click chart segments to drill into individual items.</p>
            </TooltipContent>
          </Tooltip>
        </div>
        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger>
              <div className="flex items-center gap-2">
                <Sparkles className={cn('h-4 w-4', useAi ? 'text-primary' : 'text-muted-foreground')} />
                <Switch
                  checked={useAi}
                  onCheckedChange={(checked) => {
                    if (checked && aiSettings && !aiSettings.feature_work_categorization) {
                      toast.error('AI classification is disabled. Enable it in AI Settings.')
                      return
                    }
                    setUseAi(checked)
                  }}
                  disabled={isLoading}
                />
                <span className="text-sm text-muted-foreground">AI Classify</span>
              </div>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p>Uses Claude API to classify items that couldn't be determined from labels or title keywords. Requires ANTHROPIC_API_KEY.</p>
            </TooltipContent>
          </Tooltip>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          title="Merged PRs"
          value={data.total_prs}
          tooltip="Total merged pull requests in the selected period, classified by work category."
        />
        <StatCard
          title="Issues Created"
          value={data.total_issues}
          tooltip="Total issues created by team members in the selected period."
        />
        <StatCard
          title="Unclassified"
          value={`${data.unknown_pct}%`}
          tooltip="Percentage of items that couldn't be classified by labels or title keywords. Click the Unknown segment in the charts to review and reclassify."
          subtitle={useAi && data.ai_classified_count > 0 ? `${data.ai_classified_count} AI-classified` : undefined}
        />
      </div>

      {/* Donut charts */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* PR Donut */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              PR Allocation by Category
            </CardTitle>
          </CardHeader>
          <CardContent>
            {prDonutData.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">No PR data.</p>
            ) : (
              <>
                <div className="relative">
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie
                        data={prDonutData}
                        cx="50%"
                        cy="50%"
                        innerRadius={70}
                        outerRadius={100}
                        paddingAngle={2}
                        dataKey="value"
                        cursor="pointer"
                        onClick={(_, index) => {
                          const cat = prDonutData[index].category
                          setSelectedPrCategory(selectedPrCategory === cat ? null : cat)
                        }}
                      >
                        {prDonutData.map((entry) => (
                          <Cell
                            key={`${pieId}-pr-${entry.name}`}
                            fill={entry.color}
                            opacity={selectedPrCategory && selectedPrCategory !== entry.category ? 0.3 : 1}
                            stroke={selectedPrCategory === entry.category ? entry.color : 'transparent'}
                            strokeWidth={selectedPrCategory === entry.category ? 3 : 0}
                          />
                        ))}
                      </Pie>
                      <RechartsTooltip content={<ChartTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="text-center">
                      <div className="text-2xl font-bold">{totalPrCount}</div>
                      <div className="text-[10px] text-muted-foreground">PRs</div>
                    </div>
                  </div>
                </div>
                <CategoryLegend
                  data={prDonutData}
                  selected={selectedPrCategory}
                  onSelect={setSelectedPrCategory}
                />
                {selectedPrCategory && (
                  <CategoryPreview
                    category={selectedPrCategory}
                    itemType="pr"
                    dateFrom={dateFrom}
                    dateTo={dateTo}
                  />
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Issue Donut */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Issue Allocation by Category
            </CardTitle>
          </CardHeader>
          <CardContent>
            {issueDonutData.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">No issue data.</p>
            ) : (
              <>
                <div className="relative">
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie
                        data={issueDonutData}
                        cx="50%"
                        cy="50%"
                        innerRadius={70}
                        outerRadius={100}
                        paddingAngle={2}
                        dataKey="value"
                        cursor="pointer"
                        onClick={(_, index) => {
                          const cat = issueDonutData[index].category
                          setSelectedIssueCategory(selectedIssueCategory === cat ? null : cat)
                        }}
                      >
                        {issueDonutData.map((entry) => (
                          <Cell
                            key={`${pieId}-issue-${entry.name}`}
                            fill={entry.color}
                            opacity={selectedIssueCategory && selectedIssueCategory !== entry.category ? 0.3 : 1}
                            stroke={selectedIssueCategory === entry.category ? entry.color : 'transparent'}
                            strokeWidth={selectedIssueCategory === entry.category ? 3 : 0}
                          />
                        ))}
                      </Pie>
                      <RechartsTooltip content={<ChartTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="text-center">
                      <div className="text-2xl font-bold">{totalIssueCount}</div>
                      <div className="text-[10px] text-muted-foreground">Issues</div>
                    </div>
                  </div>
                </div>
                <CategoryLegend
                  data={issueDonutData}
                  selected={selectedIssueCategory}
                  onSelect={setSelectedIssueCategory}
                />
                {selectedIssueCategory && (
                  <CategoryPreview
                    category={selectedIssueCategory}
                    itemType="issue"
                    dateFrom={dateFrom}
                    dateTo={dateTo}
                  />
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Trend chart */}
      {trendData.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Investment Over Time ({data.period_type === 'weekly' ? 'Weekly' : 'Monthly'})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="label" fontSize={12} stroke="hsl(var(--muted-foreground))" />
                <YAxis fontSize={12} stroke="hsl(var(--muted-foreground))" />
                <RechartsTooltip content={<TrendTooltip />} />
                <Legend />
                {CATEGORY_ORDER.filter((cat) => cat !== 'unknown').map((cat) => (
                  <Bar
                    key={cat}
                    dataKey={cat}
                    stackId="a"
                    name={CATEGORY_CONFIG[cat].label}
                    fill={CATEGORY_CONFIG[cat].color}
                  />
                ))}
                <Bar
                  dataKey="unknown"
                  stackId="a"
                  name={CATEGORY_CONFIG.unknown.label}
                  fill={CATEGORY_CONFIG.unknown.color}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Developer breakdown */}
      {sortedDevs.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Developer Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Developer</TableHead>
                  <TableHead className="cursor-pointer select-none" onClick={() => toggleSort('total_prs')}>
                    PRs {sortKey === 'total_prs' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                  </TableHead>
                  {CATEGORY_ORDER.map((cat) => (
                    <TableHead
                      key={cat}
                      className="cursor-pointer text-center select-none"
                      onClick={() => toggleSort(cat)}
                    >
                      <span style={{ color: CATEGORY_CONFIG[cat].color }}>
                        {CATEGORY_CONFIG[cat].label}
                      </span>
                      {sortKey === cat ? (sortDir === 'desc' ? ' ↓' : ' ↑') : ''}
                    </TableHead>
                  ))}
                  <TableHead className="cursor-pointer select-none" onClick={() => toggleSort('total_issues')}>
                    Issues {sortKey === 'total_issues' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedDevs.map((dev) => (
                  <TableRow key={dev.developer_id}>
                    <TableCell>
                      <div>
                        <Link to={`/team/${dev.developer_id}`} className="font-medium hover:underline">
                          {dev.display_name}
                        </Link>
                        {dev.team && (
                          <div className="text-xs text-muted-foreground">{dev.team}</div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{dev.total_prs}</TableCell>
                    {CATEGORY_ORDER.map((cat) => {
                      const count = dev.pr_categories[cat] ?? 0
                      const pct =
                        dev.total_prs > 0 ? Math.round((count / dev.total_prs) * 100) : 0
                      return (
                        <TableCell key={cat} className="text-center">
                          {count > 0 ? (
                            <div className="flex flex-col items-center gap-0.5">
                              <span>{count}</span>
                              <div
                                className="h-1 rounded-full"
                                style={{
                                  width: `${Math.max(pct, 4)}%`,
                                  backgroundColor: CATEGORY_CONFIG[cat].color,
                                  minWidth: count > 0 ? '4px' : '0px',
                                }}
                              />
                            </div>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                      )
                    })}
                    <TableCell>{dev.total_issues}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
