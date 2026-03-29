import { Info } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { SyncError } from '@/utils/types'

interface SyncErrorDetailProps {
  errors: SyncError[]
}

const ERROR_TYPE_LABELS: Record<string, string> = {
  config: 'Configuration',
  auth: 'Authentication',
  github_api: 'GitHub API',
  timeout: 'Timeout',
  unknown: 'Unknown',
}

export default function SyncErrorDetail({ errors }: SyncErrorDetailProps) {
  if (errors.length === 0) return null

  // Group errors by repo
  const grouped = new Map<string, SyncError[]>()
  for (const err of errors) {
    const key = err.repo ?? 'General'
    const list = grouped.get(key) || []
    list.push(err)
    grouped.set(key, list)
  }

  return (
    <div className="space-y-3">
      {Array.from(grouped.entries()).map(([repo, repoErrors]) => (
        <div key={repo} className="space-y-1.5">
          <div className="text-sm font-medium">{repo}</div>
          {repoErrors.map((err, i) => (
            <div key={i} className="space-y-1">
              <div className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-xs">
                <Badge
                  variant={err.error_type === 'config' ? 'outline' : err.retryable ? 'outline' : 'destructive'}
                  className={
                    err.error_type === 'config'
                      ? 'border-blue-500/50 text-blue-600'
                      : err.retryable
                        ? 'border-amber-500/50 text-amber-600'
                        : ''
                  }
                >
                  {err.error_type === 'config' ? 'Config' : err.retryable ? 'Retryable' : 'Permanent'}
                </Badge>
                <span className="font-medium">{err.step}</span>
                {err.status_code && (
                  <span className="text-muted-foreground">HTTP {err.status_code}</span>
                )}
                <span className="text-muted-foreground">
                  {ERROR_TYPE_LABELS[err.error_type] ?? err.error_type}
                </span>
                {err.attempt > 1 && (
                  <span className="text-muted-foreground">attempt {err.attempt}</span>
                )}
              </div>
              <div className="px-3 text-xs text-muted-foreground break-all">
                {err.message}
              </div>
              {err.hint && (
                <div className="mx-3 flex items-start gap-1.5 rounded-md bg-blue-50 px-3 py-2 text-xs text-blue-700 dark:bg-blue-950/30 dark:text-blue-400">
                  <Info className="mt-0.5 h-3 w-3 shrink-0" />
                  <span>{err.hint}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
