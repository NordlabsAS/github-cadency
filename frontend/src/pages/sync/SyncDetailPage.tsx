import { useParams, Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowLeft, CheckCircle2, AlertTriangle, XCircle, Ban } from 'lucide-react'
import { useSyncEvent, useResumeSync } from '@/hooks/useSync'
import ErrorCard from '@/components/ErrorCard'
import SyncProgressView from './SyncProgressView'
import SyncErrorDetail from './SyncErrorDetail'
import SyncLogViewer from './SyncLogViewer'
import type { SyncEvent, SyncError } from '@/utils/types'
import { formatDuration, formatDate } from '@/utils/format'

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

function RepoStatusIcon({ status }: { status: string }) {
  if (status === 'ok') return <CheckCircle2 className="h-4 w-4 text-green-500" />
  if (status === 'partial') return <AlertTriangle className="h-4 w-4 text-amber-500" />
  return <XCircle className="h-4 w-4 text-red-500" />
}

export default function SyncDetailPage() {
  const { id } = useParams<{ id: string }>()
  const eventId = id ? parseInt(id, 10) : undefined
  const { data: event, isLoading, isError, refetch } = useSyncEvent(eventId)
  const resumeSync = useResumeSync()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Link to="/admin/sync"><Button variant="ghost" size="sm"><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button></Link>
          <h1 className="text-2xl font-bold">Sync Details</h1>
        </div>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      </div>
    )
  }

  if (isError || !event) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Link to="/admin/sync"><Button variant="ghost" size="sm"><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button></Link>
          <h1 className="text-2xl font-bold">Sync Details</h1>
        </div>
        <ErrorCard message="Could not load sync event." onRetry={() => refetch()} />
      </div>
    )
  }

  const isActive = event.status === 'started'
  const errors = (event.errors ?? []).filter(
    (e): e is SyncError => e != null && typeof e === 'object' && 'step' in e
  )
  const completedRepos = event.repos_completed ?? []
  const failedRepos = event.repos_failed ?? []
  const logs = event.log_summary ?? []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to="/admin/sync"><Button variant="ghost" size="sm"><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button></Link>
        <h1 className="text-2xl font-bold">Sync #{event.id}</h1>
        <span className="text-sm text-muted-foreground">{event.sync_scope ?? event.sync_type}</span>
        {event.triggered_by && (
          <Badge variant="secondary" className="text-xs">
            {event.triggered_by === 'scheduled' ? 'Auto' : event.triggered_by === 'auto_resume' ? 'Resumed' : 'Manual'}
          </Badge>
        )}
        <Badge variant={statusVariant(event.status)}>{statusLabel(event.status)}</Badge>
        {event.resumed_from_id && (
          <Link to={`/admin/sync/${event.resumed_from_id}`}>
            <Badge variant="outline" className="border-blue-500/50 text-blue-600 cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-950/30">
              Resumed from #{event.resumed_from_id}
            </Badge>
          </Link>
        )}
        {event.is_resumable && !isActive && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => resumeSync.mutate(event.id)}
            disabled={resumeSync.isPending}
          >
            Resume
          </Button>
        )}
      </div>

      {/* Active sync — live progress */}
      {isActive && <SyncProgressView sync={event} />}

      {/* Summary stats (for completed syncs) */}
      {!isActive && (() => {
        const totalSkipped = completedRepos.reduce(
          (sum, r) => sum + (r.prs_skipped ?? 0) + (r.issues_skipped ?? 0), 0
        )
        return (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-muted-foreground">Repos</div>
                <div className="text-lg font-bold">
                  {completedRepos.length}/{event.total_repos ?? '-'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-muted-foreground">PRs Synced</div>
                <div className="text-lg font-bold">{event.prs_upserted ?? 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-muted-foreground">Issues Synced</div>
                <div className="text-lg font-bold">{event.issues_upserted ?? 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-muted-foreground">Duration</div>
                <div className="text-lg font-bold">{formatDuration(event.duration_s)}</div>
              </CardContent>
            </Card>
            {totalSkipped > 0 ? (
              <Card>
                <CardContent className="pt-4 pb-4">
                  <div className="text-xs text-muted-foreground">Unchanged (Skipped)</div>
                  <div className="text-lg font-bold text-blue-600">{totalSkipped}</div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="pt-4 pb-4">
                  <div className="text-xs text-muted-foreground">Started</div>
                  <div className="text-sm font-medium">{formatDate(event.started_at)}</div>
                </CardContent>
              </Card>
            )}
          </div>
        )
      })()}

      {/* Per-repo results */}
      {(completedRepos.length > 0 || failedRepos.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Repository Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {completedRepos.map((repo) => (
                <RepoResultRow key={repo.repo_id} repo={repo} />
              ))}
              {failedRepos.map((repo) => (
                <div
                  key={repo.repo_id}
                  className="flex items-center gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 dark:border-red-900 dark:bg-red-950/30"
                >
                  <XCircle className="h-4 w-4 shrink-0 text-red-500" />
                  <span className="font-medium text-sm">{repo.repo_name}</span>
                  <Badge variant="destructive" className="text-xs">failed</Badge>
                  <span className="text-xs text-muted-foreground truncate flex-1">{repo.error}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Errors */}
      {errors.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Ban className="h-4 w-4 text-red-500" />
              Errors ({errors.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <SyncErrorDetail errors={errors} />
          </CardContent>
        </Card>
      )}

      {/* Full log */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Sync Log ({logs.length} entries)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <SyncLogViewer logs={logs} autoScroll={isActive} />
        </CardContent>
      </Card>
    </div>
  )
}

function RepoResultRow({ repo }: { repo: { repo_id: number; repo_name: string; status: string; prs: number; issues: number; prs_skipped?: number; issues_skipped?: number; warnings: string[] } }) {
  const totalSkipped = (repo.prs_skipped ?? 0) + (repo.issues_skipped ?? 0)
  return (
    <div className="flex items-center gap-3 rounded-md border px-4 py-3">
      <RepoStatusIcon status={repo.status} />
      <span className="font-medium text-sm min-w-0 truncate">{repo.repo_name}</span>
      <Badge variant="outline" className="text-xs shrink-0">{repo.status}</Badge>
      <div className="flex gap-4 text-xs text-muted-foreground ml-auto shrink-0">
        <span>{repo.prs} PRs</span>
        <span>{repo.issues} issues</span>
        {totalSkipped > 0 && (
          <span className="text-blue-600" title={`${repo.prs_skipped ?? 0} PRs + ${repo.issues_skipped ?? 0} issues unchanged`}>
            {totalSkipped} skipped
          </span>
        )}
      </div>
      {repo.warnings.length > 0 && (
        <span className="text-xs text-amber-600" title={repo.warnings.join('\n')}>
          <AlertTriangle className="inline h-3.5 w-3.5 mr-0.5" />
          {repo.warnings.length}
        </span>
      )}
    </div>
  )
}
