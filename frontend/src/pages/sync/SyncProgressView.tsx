import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { AlertTriangle, Loader2, Square, Zap } from 'lucide-react'
import { useCancelSync, useForceStopSync } from '@/hooks/useSync'
import SyncErrorDetail from './SyncErrorDetail'
import SyncLogViewer from './SyncLogViewer'
import type { SyncEvent } from '@/utils/types'

interface SyncProgressViewProps {
  sync: SyncEvent
  compact?: boolean
}

const STEP_LABELS: Record<string, string> = {
  fetching_prs: 'Fetching pull requests',
  processing_prs: 'Processing pull requests',
  fetching_issues: 'Fetching issues',
  processing_issues: 'Processing issues',
  processing_issue_comments: 'Fetching issue comments',
  syncing_file_tree: 'Syncing file tree',
  fetching_deployments: 'Fetching deployments',
}

function formatStepProgress(sync: SyncEvent): string | null {
  if (!sync.current_step) return null

  const label = STEP_LABELS[sync.current_step] || sync.current_step

  if (sync.current_step === 'processing_prs' && sync.current_repo_prs_total) {
    return `${label} (${sync.current_repo_prs_done ?? 0}/${sync.current_repo_prs_total})`
  }
  if (sync.current_step === 'processing_issues' && sync.current_repo_issues_total) {
    return `${label} (${sync.current_repo_issues_done ?? 0}/${sync.current_repo_issues_total})`
  }
  return label
}

function getSubProgress(sync: SyncEvent): number | null {
  if (sync.current_step === 'processing_prs' && sync.current_repo_prs_total && sync.current_repo_prs_total > 0) {
    return Math.round(((sync.current_repo_prs_done ?? 0) / sync.current_repo_prs_total) * 100)
  }
  if (sync.current_step === 'processing_issues' && sync.current_repo_issues_total && sync.current_repo_issues_total > 0) {
    return Math.round(((sync.current_repo_issues_done ?? 0) / sync.current_repo_issues_total) * 100)
  }
  return null
}

export default function SyncProgressView({ sync, compact }: SyncProgressViewProps) {
  const [elapsed, setElapsed] = useState(0)
  const [showErrors, setShowErrors] = useState(false)
  const [showLog, setShowLog] = useState(false)
  const cancelSync = useCancelSync()
  const forceStop = useForceStopSync()

  useEffect(() => {
    if (!sync.started_at) return
    const start = new Date(sync.started_at).getTime()
    const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000))
    tick()
    const interval = setInterval(tick, 1000)
    return () => clearInterval(interval)
  }, [sync.started_at])

  const completedCount = sync.repos_completed?.length ?? 0
  const failedCount = sync.repos_failed?.length ?? 0
  const totalRepos = sync.total_repos ?? 0
  const progressPct = totalRepos > 0 ? Math.round((completedCount / totalRepos) * 100) : 0

  const minutes = Math.floor(elapsed / 60)
  const seconds = elapsed % 60
  const elapsedStr = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`

  const stepProgress = formatStepProgress(sync)
  const subPct = getSubProgress(sync)

  const errors = (sync.errors ?? []).filter(
    (e): e is NonNullable<typeof e> => e != null && typeof e === 'object'
  )

  // Show force stop when sync is stale (>30 min elapsed) or cancel was already requested
  const isStale = elapsed > 1800
  const showForceStop = isStale || sync.cancel_requested

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
          Sync In Progress
          <Badge variant="outline" className="ml-auto">{sync.sync_type}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {sync.sync_type === 'contributors' ? (
          /* Contributor sync: simple progress */
          <>
            <div className="flex items-center gap-2 text-sm">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
              </span>
              <span>Syncing organization contributors...</span>
            </div>
            <div className="flex gap-6 text-sm">
              {(sync.repos_synced ?? 0) > 0 && (
                <div>
                  <span className="text-muted-foreground">New developers: </span>
                  <span className="font-medium">{sync.repos_synced}</span>
                </div>
              )}
              <div>
                <span className="text-muted-foreground">Elapsed: </span>
                <span className="font-medium">{elapsedStr}</span>
              </div>
            </div>
          </>
        ) : (
          /* Full/incremental sync: repo-level progress */
          <>
            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>{completedCount} / {totalRepos} repos</span>
                <span className="text-muted-foreground">{progressPct}%</span>
              </div>
              <Progress value={progressPct} />
            </div>

            {/* Current repo + step */}
            {sync.current_repo_name && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 text-sm">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                  </span>
                  <span className="text-muted-foreground">Syncing:</span>
                  <span className="font-medium">{sync.current_repo_name}</span>
                </div>
                {stepProgress && (
                  <div className="ml-4 space-y-1">
                    <div className="text-xs text-muted-foreground">{stepProgress}</div>
                    {subPct !== null && (
                      <Progress value={subPct} className="h-1.5" />
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Counters */}
            <div className="flex gap-6 text-sm">
              <div>
                <span className="text-muted-foreground">PRs: </span>
                <span className="font-medium">{sync.prs_upserted ?? 0}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Issues: </span>
                <span className="font-medium">{sync.issues_upserted ?? 0}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Elapsed: </span>
                <span className="font-medium">{elapsedStr}</span>
              </div>
              {(sync.rate_limit_wait_s ?? 0) > 0 && (
                <div className="text-amber-600">
                  <AlertTriangle className="mr-1 inline h-3.5 w-3.5" />
                  Rate limited ({sync.rate_limit_wait_s}s wait)
                </div>
              )}
            </div>
          </>
        )}

        {/* Cancel / Force Stop (not available for contributor syncs) */}
        {sync.sync_type !== 'contributors' && <div className="flex items-center gap-2">
          {!sync.cancel_requested ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => cancelSync.mutate()}
              disabled={cancelSync.isPending}
            >
              {cancelSync.isPending ? (
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Square className="mr-2 h-3.5 w-3.5" />
              )}
              Cancel Sync
            </Button>
          ) : (
            <Badge variant="outline" className="border-amber-500/50 text-amber-600">
              Cancelling...
            </Badge>
          )}
          {showForceStop && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => forceStop.mutate()}
              disabled={forceStop.isPending}
            >
              {forceStop.isPending ? (
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Zap className="mr-2 h-3.5 w-3.5" />
              )}
              Force Stop
            </Button>
          )}
        </div>}

        {/* Error count */}
        {failedCount > 0 && (
          <button
            onClick={() => setShowErrors(!showErrors)}
            className="flex items-center gap-2 text-sm text-red-600 hover:underline"
          >
            <Badge variant="destructive">{failedCount}</Badge>
            repos failed so far
          </button>
        )}
        {showErrors && (
          <>
            {errors.length > 0 && <SyncErrorDetail errors={errors} />}
            {(sync.repos_failed ?? []).length > 0 && (
              <div className="space-y-1">
                {(sync.repos_failed ?? []).map((f, i) => (
                  <div key={i} className="flex items-center gap-2 rounded-md border px-3 py-2 text-xs">
                    <Badge variant="destructive">failed</Badge>
                    <span className="font-medium">{f.repo_name}</span>
                    <span className="text-muted-foreground truncate">{f.error}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* Log toggle */}
        {!compact && (
          <>
            <button
              onClick={() => setShowLog(!showLog)}
              className="text-xs text-muted-foreground hover:underline"
            >
              {showLog ? 'Hide' : 'Show'} sync log ({(sync.log_summary ?? []).length} entries)
            </button>
            {showLog && <SyncLogViewer logs={sync.log_summary ?? []} />}
          </>
        )}
      </CardContent>
    </Card>
  )
}
