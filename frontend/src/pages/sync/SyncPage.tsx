import { AlertTriangle, XCircle } from 'lucide-react'
import { useSyncStatus, useSyncEvents, usePreflight } from '@/hooks/useSync'
import ErrorCard from '@/components/ErrorCard'
import TableSkeleton from '@/components/TableSkeleton'
import SyncOverviewPanel from './SyncOverviewPanel'
import SyncProgressView from './SyncProgressView'
import SyncWizard from './SyncWizard'
import ResumeBanner from './ResumeBanner'
import SyncHistoryTable from './SyncHistoryTable'
import type { PreflightCheck } from '@/utils/types'

function PreflightBanner({ checks, ready }: { checks: PreflightCheck[]; ready: boolean }) {
  const issues = checks.filter((c) => c.status !== 'ok')
  if (ready && issues.length === 0) return null

  return (
    <div className={`rounded-lg border p-4 space-y-2 ${
      ready ? 'border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/20'
            : 'border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/20'
    }`}>
      <div className={`flex items-center gap-2 text-sm font-medium ${
        ready ? 'text-amber-700 dark:text-amber-400' : 'text-red-700 dark:text-red-400'
      }`}>
        <AlertTriangle className="h-4 w-4" />
        {ready ? 'Configuration warnings' : 'Configuration errors — sync will fail until fixed'}
      </div>
      <div className="space-y-1.5">
        {issues.map((c) => (
          <div key={c.field} className="flex items-start gap-2 text-xs">
            {c.status === 'error' ? (
              <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
            ) : (
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
            )}
            <div>
              <span className="font-medium">{c.field}:</span>{' '}
              <span className="text-muted-foreground">{c.message}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function SyncPage() {
  const { data: status, isLoading: statusLoading, isError: statusError, refetch: refetchStatus } = useSyncStatus()
  const { data: events, isLoading: eventsLoading, isError: eventsError, refetch: refetchEvents } = useSyncEvents()
  const { data: preflight } = usePreflight()

  if (statusError) {
    return <ErrorCard message="Could not load sync status." onRetry={() => refetchStatus()} />
  }

  // Find the most recent resumable event (not the active one)
  const resumableEvent = !status?.active_sync
    ? (events ?? []).find((e) => e.is_resumable && e.status !== 'started')
    : undefined

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Sync</h1>

      {/* Preflight config warnings */}
      {preflight && !preflight.ready && (
        <PreflightBanner checks={preflight.checks} ready={preflight.ready} />
      )}
      {preflight && preflight.ready && preflight.checks.some((c) => c.status === 'warn') && (
        <PreflightBanner checks={preflight.checks} ready={preflight.ready} />
      )}

      {/* Overview stats */}
      {statusLoading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ) : status ? (
        <SyncOverviewPanel status={status} />
      ) : null}

      {/* Resume banner */}
      {resumableEvent && (
        <ResumeBanner
          event={resumableEvent}
          onStartFresh={() => {/* wizard handles fresh start */}}
        />
      )}

      {/* Active sync progress OR wizard */}
      {status?.active_sync ? (
        <SyncProgressView sync={status.active_sync} />
      ) : (
        <SyncWizard />
      )}

      {/* Sync history */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Sync History</h2>
        {eventsError ? (
          <ErrorCard message="Could not load sync events." onRetry={() => refetchEvents()} />
        ) : eventsLoading ? (
          <TableSkeleton
            columns={8}
            rows={5}
            headers={['Type', 'Status', 'Progress', 'PRs', 'Issues', 'Errors', 'Duration', 'Started']}
          />
        ) : (
          <SyncHistoryTable events={events ?? []} />
        )}
      </div>
    </div>
  )
}
