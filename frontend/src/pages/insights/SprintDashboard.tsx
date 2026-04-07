import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'
import { AlertTriangle, ExternalLink } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import StatCard from '@/components/StatCard'
import ErrorCard from '@/components/ErrorCard'
import {
  useSprintVelocity, useSprintCompletion, useScopeCreep,
  useSprints, useSprintDetail,
} from '@/hooks/useSprints'
import { useIntegrations } from '@/hooks/useIntegrations'

export default function SprintDashboard() {
  const { data: integrations } = useIntegrations()
  const hasLinear = integrations?.some((i) => i.type === 'linear' && i.status === 'active')

  const [teamKey, setTeamKey] = useState<string>()
  const [selectedSprintId, setSelectedSprintId] = useState<number>()

  const { data: velocity, isLoading: velLoading, isError: velError, refetch: refetchVel } = useSprintVelocity(teamKey)
  const { data: completion, isLoading: compLoading } = useSprintCompletion(teamKey)
  const { data: scopeCreep, isLoading: creepLoading } = useScopeCreep(teamKey)
  const { data: sprints } = useSprints(teamKey, undefined, 20)
  const { data: detail } = useSprintDetail(selectedSprintId)

  // Extract unique team keys from sprints
  const teams = useMemo(() => {
    if (!sprints) return []
    const keys = new Set(sprints.map((s) => s.team_key).filter(Boolean) as string[])
    return Array.from(keys).sort()
  }, [sprints])

  if (!hasLinear) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Sprints</h1>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
            <AlertTriangle className="h-10 w-10 text-muted-foreground" />
            <div>
              <p className="font-medium">No Linear integration configured</p>
              <p className="text-sm text-muted-foreground">
                Connect Linear to see sprint velocity, completion rates, and scope creep.
              </p>
            </div>
            <Link
              to="/admin/integrations"
              className="text-sm font-medium text-blue-600 hover:underline dark:text-blue-400"
            >
              Go to Integration Settings &rarr;
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (velError) return <ErrorCard message="Could not load sprint data." onRetry={refetchVel} />

  const isLoading = velLoading || compLoading || creepLoading
  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Sprints</h1>
        <div className="grid gap-4 sm:grid-cols-3">
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
        </div>
        <Skeleton className="h-72 rounded-lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Sprints</h1>
        {teams.length > 0 && (
          <Select value={teamKey ?? '__all__'} onValueChange={(v) => setTeamKey(!v || v === '__all__' ? undefined : v)}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="All teams" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All teams</SelectItem>
              {teams.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Summary stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          title="Avg Velocity"
          value={velocity?.avg_velocity ?? 0}
          tooltip="Average completed scope per sprint"
        />
        <StatCard
          title="Avg Completion"
          value={`${completion?.avg_completion_rate ?? 0}%`}
          tooltip="Average % of planned scope delivered"
        />
        <StatCard
          title="Avg Scope Creep"
          value={`${scopeCreep?.avg_scope_creep_pct ?? 0}%`}
          tooltip="Average % of scope added mid-sprint"
        />
      </div>

      {/* Velocity chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Velocity Trend</CardTitle>
        </CardHeader>
        <CardContent>
          {velocity?.data.length ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={velocity.data}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="sprint_name"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v) => v ?? ''}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="completed_scope" name="Completed" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
                <Bar dataKey="planned_scope" name="Planned" fill="hsl(var(--chart-2))" radius={[4, 4, 0, 0]} opacity={0.4} />
                <ReferenceLine y={velocity.avg_velocity} stroke="hsl(var(--chart-3))" strokeDasharray="3 3" label="Avg" />
                <Legend />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="py-8 text-center text-sm text-muted-foreground">No closed sprints yet</p>
          )}
        </CardContent>
      </Card>

      {/* Completion & Scope Creep side by side */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Completion Rate</CardTitle>
          </CardHeader>
          <CardContent>
            {completion?.data.length ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={completion.data}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="sprint_name" tick={{ fontSize: 11 }} tickFormatter={(v) => v ?? ''} />
                  <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} unit="%" />
                  <Tooltip formatter={(v) => `${v}%`} />
                  <Line type="monotone" dataKey="completion_rate" stroke="hsl(var(--chart-1))" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">No data</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Scope Creep</CardTitle>
          </CardHeader>
          <CardContent>
            {scopeCreep?.data.length ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={scopeCreep.data}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="sprint_name" tick={{ fontSize: 11 }} tickFormatter={(v) => v ?? ''} />
                  <YAxis tick={{ fontSize: 11 }} unit="%" />
                  <Tooltip formatter={(v) => `${v}%`} />
                  <Bar dataKey="scope_creep_pct" name="Scope Creep %" fill="hsl(var(--chart-4))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">No data</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Sprint selector + detail */}
      {sprints && sprints.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Sprint Detail</CardTitle>
              <Select
                value={selectedSprintId ? String(selectedSprintId) : '__none__'}
                onValueChange={(v) => setSelectedSprintId(v === '__none__' ? undefined : Number(v))}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select sprint..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">Select sprint...</SelectItem>
                  {sprints.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.name ?? `Sprint ${s.number}`}
                      {s.state === 'active' && ' (active)'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          {detail && (
            <CardContent>
              <div className="mb-4 flex gap-3 text-sm">
                <Badge variant="outline">{detail.state}</Badge>
                {detail.completion_rate != null && (
                  <Badge variant="outline">{detail.completion_rate}% complete</Badge>
                )}
                {detail.scope_creep_pct != null && (
                  <Badge variant="outline">{detail.scope_creep_pct}% creep</Badge>
                )}
              </div>
              {detail.issues.length > 0 ? (
                <div className="max-h-80 overflow-y-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Issue</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Priority</TableHead>
                        <TableHead>Estimate</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detail.issues.map((issue) => (
                        <TableRow key={issue.id}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-xs text-muted-foreground">{issue.identifier}</span>
                              <span className="truncate">{issue.title}</span>
                              {issue.url && (
                                <a href={issue.url} target="_blank" rel="noopener noreferrer">
                                  <ExternalLink className="h-3 w-3 text-muted-foreground" />
                                </a>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <StatusBadge category={issue.status_category} />
                          </TableCell>
                          <TableCell>
                            <PriorityBadge priority={issue.priority} label={issue.priority_label} />
                          </TableCell>
                          <TableCell>{issue.estimate ?? '—'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No issues in this sprint</p>
              )}
            </CardContent>
          )}
        </Card>
      )}
    </div>
  )
}

function StatusBadge({ category }: { category: string | null }) {
  const colors: Record<string, string> = {
    done: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
    in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    todo: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
    triage: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
    cancelled: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  }
  const label = category?.replace('_', ' ') ?? 'unknown'
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${colors[category ?? ''] ?? colors.todo}`}>
      {label}
    </span>
  )
}

function PriorityBadge({ priority, label }: { priority: number; label: string | null }) {
  const colors: Record<number, string> = {
    1: 'text-red-600 dark:text-red-400',
    2: 'text-amber-600 dark:text-amber-400',
    3: 'text-blue-600 dark:text-blue-400',
    4: 'text-muted-foreground',
  }
  return <span className={`text-xs font-medium ${colors[priority] ?? 'text-muted-foreground'}`}>{label ?? '—'}</span>
}
