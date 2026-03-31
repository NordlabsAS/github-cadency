import { Card, CardContent } from '@/components/ui/card'
import { Database, Clock, RefreshCw, BarChart3, Timer } from 'lucide-react'
import type { SyncStatusResponse } from '@/utils/types'
import { timeAgo, formatDuration } from '@/utils/format'

interface SyncOverviewPanelProps {
  status: SyncStatusResponse
}

function formatNextSync(lastSync: string | null, intervalMinutes: number): string {
  if (!lastSync) return `Every ${intervalMinutes}m`
  const nextTime = new Date(lastSync).getTime() + intervalMinutes * 60_000
  const remainingMs = nextTime - Date.now()
  if (remainingMs <= 0) return 'Soon'
  const minutes = Math.ceil(remainingMs / 60_000)
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    return `~${hours}h ${minutes % 60}m`
  }
  return `~${minutes}m`
}

export default function SyncOverviewPanel({ status }: SyncOverviewPanelProps) {
  const schedule = status.schedule

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
      <Card size="sm">
        <CardContent className="flex items-center gap-3">
          <Database className="h-4 w-4 text-muted-foreground" />
          <div>
            <div className="text-lg font-bold">
              {status.tracked_repos_count}/{status.total_repos_count}
            </div>
            <div className="text-xs text-muted-foreground">Tracked Repos</div>
          </div>
        </CardContent>
      </Card>

      <Card size="sm">
        <CardContent className="flex items-center gap-3">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <div>
            <div className="text-lg font-bold">
              {timeAgo(status.last_successful_sync)}
            </div>
            <div className="text-xs text-muted-foreground">Last Sync</div>
          </div>
        </CardContent>
      </Card>

      <Card size="sm">
        <CardContent className="flex items-center gap-3">
          <RefreshCw className="h-4 w-4 text-muted-foreground" />
          <div>
            <div className="text-lg font-bold">
              {formatDuration(status.last_sync_duration_s)}
            </div>
            <div className="text-xs text-muted-foreground">Last Duration</div>
          </div>
        </CardContent>
      </Card>

      <Card size="sm">
        <CardContent className="flex items-center gap-3">
          <BarChart3 className="h-4 w-4 text-muted-foreground" />
          <div>
            <div className="text-lg font-bold">
              {status.last_completed?.status === 'completed'
                ? 'Healthy'
                : status.last_completed?.status === 'completed_with_errors'
                  ? 'Partial'
                  : status.last_completed?.status === 'failed'
                    ? 'Failed'
                    : '-'}
            </div>
            <div className="text-xs text-muted-foreground">Last Status</div>
          </div>
        </CardContent>
      </Card>

      <Card size="sm">
        <CardContent className="flex items-center gap-3">
          <Timer className="h-4 w-4 text-muted-foreground" />
          <div>
            {schedule?.auto_sync_enabled ? (
              <>
                <div className="text-lg font-bold">
                  {formatNextSync(status.last_successful_sync, schedule.incremental_interval_minutes)}
                </div>
                <div className="text-xs text-muted-foreground">
                  Next sync (every {schedule.incremental_interval_minutes}m)
                </div>
              </>
            ) : (
              <>
                <div className="text-lg font-bold text-muted-foreground">Disabled</div>
                <div className="text-xs text-muted-foreground">Auto-sync</div>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
