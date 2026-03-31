import { useNavigate } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import type { SyncEvent } from '@/utils/types'
import { timeAgo, formatDuration } from '@/utils/format'

interface SyncHistoryTableProps {
  events: SyncEvent[]
}

function statusVariant(status: string | null) {
  switch (status) {
    case 'completed': return 'default' as const
    case 'started': return 'secondary' as const
    case 'failed': return 'destructive' as const
    case 'cancelled': return 'outline' as const
    case 'completed_with_errors': return 'outline' as const
    default: return 'outline' as const
  }
}

function statusLabel(status: string | null): string {
  if (status === 'completed_with_errors') return 'partial'
  return status ?? '-'
}

export default function SyncHistoryTable({ events }: SyncHistoryTableProps) {
  const navigate = useNavigate()

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Scope</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Progress</TableHead>
            <TableHead>PRs</TableHead>
            <TableHead>Issues</TableHead>
            <TableHead>Errors</TableHead>
            <TableHead>Duration</TableHead>
            <TableHead>Started</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {events.map((event) => {
            const isActive = event.status === 'started'
            const errorCount = (event.errors ?? []).length
            const failedCount = (event.repos_failed ?? []).length
            const completedCount = event.repos_completed?.length ?? event.repos_synced ?? 0
            const totalRepos = event.total_repos

            return (
              <TableRow
                key={event.id}
                className={cn(
                  'cursor-pointer hover:bg-muted/50',
                  isActive && 'border-l-4 border-l-primary',
                )}
                onClick={() => navigate(`/admin/sync/${event.id}`)}
              >
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm truncate max-w-[200px]" title={event.sync_scope ?? event.sync_type ?? ''}>
                      {event.sync_scope ?? event.sync_type ?? '-'}
                    </span>
                    {event.triggered_by && (
                      <Badge variant="secondary" className="text-[10px] px-1.5 py-0 shrink-0">
                        {event.triggered_by === 'scheduled' ? 'Auto' : event.triggered_by === 'auto_resume' ? 'Resumed' : 'Manual'}
                      </Badge>
                    )}
                    {!event.triggered_by && event.resumed_from_id && (
                      <span className="text-xs text-muted-foreground" title={`Resumed from #${event.resumed_from_id}`}>
                        &#x21bb;
                      </span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    {isActive && (
                      <span className="relative flex h-2 w-2">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                      </span>
                    )}
                    <Badge variant={statusVariant(event.status)}>
                      {statusLabel(event.status)}
                    </Badge>
                  </div>
                </TableCell>
                <TableCell>
                  {totalRepos != null
                    ? `${completedCount}/${totalRepos}`
                    : event.repos_synced ?? '-'}
                </TableCell>
                <TableCell>{event.prs_upserted ?? '-'}</TableCell>
                <TableCell>{event.issues_upserted ?? '-'}</TableCell>
                <TableCell>
                  {errorCount > 0 || failedCount > 0 ? (
                    <Badge variant="destructive">
                      {errorCount + failedCount}
                    </Badge>
                  ) : (
                    '-'
                  )}
                </TableCell>
                <TableCell>{formatDuration(event.duration_s)}</TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {timeAgo(event.started_at)}
                </TableCell>
              </TableRow>
            )
          })}
          {events.length === 0 && (
            <TableRow>
              <TableCell colSpan={8} className="text-center text-muted-foreground">
                No sync events yet. Trigger a sync to get started.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
