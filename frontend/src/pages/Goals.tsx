import { useState } from 'react'
import { useDevelopers } from '@/hooks/useDevelopers'
import {
  useGoals,
  useGoalProgress,
  useUpdateAdminGoal,
  useUpdateSelfGoal,
} from '@/hooks/useGoals'
import { useAuth } from '@/hooks/useAuth'
import ErrorCard from '@/components/ErrorCard'
import TableSkeleton from '@/components/TableSkeleton'
import GoalCreateDialog, { metricKeyLabels } from '@/components/GoalCreateDialog'
import GoalSparkline from '@/components/charts/GoalSparkline'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { GoalResponse, GoalProgressResponse, Developer } from '@/utils/types'

const TABLE_HEADERS = ['Developer', 'Goal', 'Metric', 'Progress', 'Sparkline', 'Status', 'Due', 'Actions']

function GoalProgressCell({ goal, progress }: { goal: GoalResponse; progress: GoalProgressResponse | undefined }) {
  const baseline = goal.baseline_value ?? 0
  const current = progress?.current_value ?? baseline
  const target = goal.target_value
  const pct = target !== baseline
    ? Math.min(100, Math.max(0, ((current - baseline) / (target - baseline)) * 100))
    : 0

  return (
    <div className="min-w-[140px]">
      <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
        <span>{baseline.toFixed(1)}</span>
        <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span>{target}</span>
      </div>
      <p className="text-xs">
        Current: <span className="font-medium">{current.toFixed(1)}</span>
      </p>
    </div>
  )
}

function GoalRow({
  goal,
  developerName,
  showDeveloperColumn,
  isAdmin,
  userId,
}: {
  goal: GoalResponse
  developerName: string
  showDeveloperColumn: boolean
  isAdmin: boolean
  userId: number | undefined
}) {
  const { data: progress } = useGoalProgress(goal.id)

  return (
    <TableRow>
      {showDeveloperColumn && (
        <TableCell className="font-medium">{developerName}</TableCell>
      )}
      <TableCell>
        <div>
          <p className="font-medium text-sm">{goal.title}</p>
          {goal.notes && (
            <p className="text-xs text-muted-foreground truncate max-w-[200px]">{goal.notes}</p>
          )}
        </div>
      </TableCell>
      <TableCell className="text-sm">
        {metricKeyLabels[goal.metric_key] ?? goal.metric_key}
      </TableCell>
      <TableCell>
        <GoalProgressCell goal={goal} progress={progress} />
      </TableCell>
      <TableCell>
        {progress && progress.history.length > 0 && (
          <GoalSparkline history={progress.history} targetValue={goal.target_value} />
        )}
      </TableCell>
      <TableCell>
        <Badge variant={statusBadgeVariant(goal.status)}>{goal.status}</Badge>
      </TableCell>
      <TableCell>
        {goal.target_date ? (
          <div className="text-sm">
            <p>{new Date(goal.target_date).toLocaleDateString()}</p>
            <p className={`text-xs ${daysRemaining(goal.target_date) === 'overdue' ? 'text-destructive' : 'text-muted-foreground'}`}>
              {daysRemaining(goal.target_date)}
            </p>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">No date</span>
        )}
      </TableCell>
      <TableCell>
        <GoalRowActions goal={goal} isAdmin={isAdmin} userId={userId} />
      </TableCell>
    </TableRow>
  )
}

function statusBadgeVariant(status: string) {
  if (status === 'achieved') return 'default' as const
  if (status === 'abandoned') return 'destructive' as const
  return 'secondary' as const
}

function daysRemaining(targetDate: string | null): string | null {
  if (!targetDate) return null
  const diff = Math.ceil((new Date(targetDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
  if (diff < 0) return 'overdue'
  if (diff === 0) return 'today'
  return `${diff}d left`
}

interface GoalRowActionsProps {
  goal: GoalResponse
  isAdmin: boolean
  userId: number | undefined
}

function GoalRowActions({ goal, isAdmin, userId }: GoalRowActionsProps) {
  const updateAdmin = useUpdateAdminGoal()
  const updateSelf = useUpdateSelfGoal()

  if (goal.status !== 'active') return null

  const canAdminUpdate = isAdmin
  const canSelfUpdate = goal.developer_id === userId && goal.created_by === 'self'

  if (!canAdminUpdate && !canSelfUpdate) return null

  const isPending = updateAdmin.isPending || updateSelf.isPending

  const handleUpdate = (status: 'achieved' | 'abandoned') => {
    if (canAdminUpdate) {
      updateAdmin.mutate({ goalId: goal.id, data: { status } })
    } else {
      updateSelf.mutate({ goalId: goal.id, data: { status } })
    }
  }

  return (
    <div className="flex gap-1">
      <Button
        variant="ghost"
        size="sm"
        className="text-xs h-7"
        disabled={isPending}
        onClick={() => handleUpdate('achieved')}
      >
        Achieve
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="text-xs h-7 text-muted-foreground"
        disabled={isPending}
        onClick={() => handleUpdate('abandoned')}
      >
        Abandon
      </Button>
    </div>
  )
}

export default function Goals() {
  const { user, isAdmin } = useAuth()
  const [filterDevId, setFilterDevId] = useState<string>('all')

  const { data: developers, isLoading: devsLoading, isError: devsError, refetch: refetchDevs } = useDevelopers()

  // Determine which developer IDs to fetch goals for
  const devIds: number[] = isAdmin
    ? filterDevId === 'all'
      ? (developers ?? []).map((d) => d.id)
      : [Number(filterDevId)]
    : user?.developer_id
      ? [user.developer_id]
      : []

  // We use a single GoalsList component that handles the multi-developer fetching
  // to avoid violating hooks rules (can't call useGoals in a loop)

  if (devsError) return <ErrorCard message="Could not load developers." onRetry={() => refetchDevs()} />
  if (devsLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{isAdmin ? 'Goals' : 'My Goals'}</h1>
        <TableSkeleton columns={8} rows={5} headers={TABLE_HEADERS} />
      </div>
    )
  }

  const devMap = new Map((developers ?? []).map((d) => [d.id, d]))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{isAdmin ? 'Goals' : 'My Goals'}</h1>
        <div className="flex items-center gap-3">
          {isAdmin && developers && (
            <Select value={filterDevId} onValueChange={(v) => v && setFilterDevId(v)}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Filter by developer" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Developers</SelectItem>
                {developers.map((d) => (
                  <SelectItem key={d.id} value={String(d.id)}>
                    {d.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <GoalCreateDialog
            developers={developers}
            isAdmin={isAdmin}
            isOwnPage={!isAdmin}
          />
        </div>
      </div>

      <GoalsTable
        devIds={devIds}
        devMap={devMap}
        isAdmin={isAdmin}
        userId={user?.developer_id}
        showDeveloperColumn={isAdmin && filterDevId === 'all'}
      />
    </div>
  )
}

interface GoalsTableProps {
  devIds: number[]
  devMap: Map<number, Developer>
  isAdmin: boolean
  userId: number | undefined
  showDeveloperColumn: boolean
}

function GoalsTable({ devIds, devMap, isAdmin, userId, showDeveloperColumn }: GoalsTableProps) {
  // Fetch goals for up to the first developer to check loading state
  // For multiple developers, we render a GoalsForDeveloper per dev to respect hooks rules
  if (devIds.length === 0) {
    return <p className="text-sm text-muted-foreground">No developers found.</p>
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            {showDeveloperColumn && <TableHead>Developer</TableHead>}
            <TableHead>Goal</TableHead>
            <TableHead>Metric</TableHead>
            <TableHead className="min-w-[180px]">Progress</TableHead>
            <TableHead>Trend</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Due</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {devIds.map((devId) => (
            <GoalsForDeveloper
              key={devId}
              developerId={devId}
              developerName={devMap.get(devId)?.display_name ?? 'Unknown'}
              showDeveloperColumn={showDeveloperColumn}
              isAdmin={isAdmin}
              userId={userId}
            />
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

interface GoalsForDeveloperProps {
  developerId: number
  developerName: string
  showDeveloperColumn: boolean
  isAdmin: boolean
  userId: number | undefined
}

function GoalsForDeveloper({
  developerId,
  developerName,
  showDeveloperColumn,
  isAdmin,
  userId,
}: GoalsForDeveloperProps) {
  const { data: goals, isLoading } = useGoals(developerId)

  if (isLoading) {
    const colSpan = showDeveloperColumn ? 8 : 7
    return (
      <TableRow>
        <TableCell colSpan={colSpan} className="text-sm text-muted-foreground">
          Loading goals{showDeveloperColumn ? ` for ${developerName}` : ''}...
        </TableCell>
      </TableRow>
    )
  }

  if (!goals || goals.length === 0) return null

  return (
    <>
      {goals.map((goal) => (
        <GoalRow
          key={goal.id}
          goal={goal}
          developerName={developerName}
          showDeveloperColumn={showDeveloperColumn}
          isAdmin={isAdmin}
          userId={userId}
        />
      ))}
    </>
  )
}
