import { useDeactivationImpact, useToggleDeveloperActive } from '@/hooks/useDevelopers'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { AlertTriangle, GitBranch, GitPullRequest, CircleDot } from 'lucide-react'
import type { Developer } from '@/utils/types'

export default function DeactivateDialog({
  developer,
  open,
  onOpenChange,
}: {
  developer: Developer
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { data: impact, isLoading } = useDeactivationImpact(developer.id, open)
  const toggle = useToggleDeveloperActive(developer.id)

  const hasOpenWork = impact && (impact.open_prs > 0 || impact.open_issues > 0)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Deactivate {developer.display_name}?</DialogTitle>
        </DialogHeader>

        <p className="text-sm text-muted-foreground">
          This will hide them from active team views, stats, and benchmarks.
          Their historical data will be preserved. They can be reactivated later.
        </p>

        {isLoading ? (
          <div className="space-y-2">
            <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
          </div>
        ) : impact && hasOpenWork ? (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400">
              <AlertTriangle className="h-4 w-4" />
              Open work that may need reassignment
            </div>
            <div className="space-y-2 text-sm">
              {impact.open_prs > 0 && (
                <div className="flex items-center gap-2">
                  <GitPullRequest className="h-3.5 w-3.5 text-muted-foreground" />
                  <span>{impact.open_prs} open pull request{impact.open_prs !== 1 ? 's' : ''}</span>
                </div>
              )}
              {impact.open_issues > 0 && (
                <div className="flex items-center gap-2">
                  <CircleDot className="h-3.5 w-3.5 text-muted-foreground" />
                  <span>{impact.open_issues} open issue{impact.open_issues !== 1 ? 's' : ''} assigned</span>
                </div>
              )}
              {impact.open_branches.length > 0 && (
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>{impact.open_branches.length} active branch{impact.open_branches.length !== 1 ? 'es' : ''}</span>
                  </div>
                  <div className="ml-5.5 flex flex-wrap gap-1">
                    {impact.open_branches.slice(0, 5).map((b) => (
                      <code key={b} className="rounded bg-muted px-1.5 py-0.5 text-xs">{b}</code>
                    ))}
                    {impact.open_branches.length > 5 && (
                      <span className="text-xs text-muted-foreground">
                        +{impact.open_branches.length - 5} more
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : impact ? (
          <p className="text-sm text-muted-foreground">
            No open pull requests, issues, or active branches found.
          </p>
        ) : null}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={toggle.isPending || isLoading}
            onClick={() => {
              toggle.mutate(false, { onSuccess: () => onOpenChange(false) })
            }}
          >
            {toggle.isPending ? 'Deactivating...' : 'Deactivate'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
