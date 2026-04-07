import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, ExternalLink, Calendar } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import ErrorCard from '@/components/ErrorCard'
import { useProjects, useProjectDetail } from '@/hooks/useSprints'
import { useIntegrations } from '@/hooks/useIntegrations'
import type { ExternalProject } from '@/utils/types'

export default function ProjectPortfolio() {
  const { data: integrations } = useIntegrations()
  const hasLinear = integrations?.some((i) => i.type === 'linear' && i.status === 'active')
  const { data: projects, isLoading, isError, refetch } = useProjects()
  const [selectedId, setSelectedId] = useState<number>()

  if (!hasLinear) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
            <AlertTriangle className="h-10 w-10 text-muted-foreground" />
            <div>
              <p className="font-medium">No Linear integration configured</p>
              <p className="text-sm text-muted-foreground">
                Connect Linear to see project health and progress.
              </p>
            </div>
            <Link to="/admin/integrations" className="text-sm font-medium text-blue-600 hover:underline dark:text-blue-400">
              Go to Integration Settings &rarr;
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isError) return <ErrorCard message="Could not load projects." onRetry={refetch} />

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-36 rounded-lg" />)}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Projects</h1>

      {!projects?.length ? (
        <p className="text-sm text-muted-foreground">No projects synced yet. Run a sync from Integration Settings.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <ProjectCard
              key={p.id}
              project={p}
              selected={selectedId === p.id}
              onSelect={() => setSelectedId(selectedId === p.id ? undefined : p.id)}
            />
          ))}
        </div>
      )}

      {selectedId && <ProjectDetailPanel projectId={selectedId} />}
    </div>
  )
}

function ProjectCard({
  project: p,
  selected,
  onSelect,
}: {
  project: ExternalProject
  selected: boolean
  onSelect: () => void
}) {
  const healthColors: Record<string, string> = {
    on_track: 'bg-emerald-500',
    at_risk: 'bg-amber-500',
    off_track: 'bg-red-500',
  }
  const healthLabels: Record<string, string> = {
    on_track: 'On Track',
    at_risk: 'At Risk',
    off_track: 'Off Track',
  }

  const progressPct = p.progress_pct != null ? Math.round(p.progress_pct * 100) : null

  return (
    <Card
      className={`cursor-pointer transition-colors hover:bg-muted/50 ${selected ? 'ring-2 ring-primary' : ''}`}
      onClick={onSelect}
    >
      <CardContent className="space-y-3 pt-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="font-medium">{p.name}</p>
            {p.status && (
              <Badge variant="outline" className="mt-1 text-xs capitalize">
                {p.status}
              </Badge>
            )}
          </div>
          {p.health && (
            <div className="flex items-center gap-1.5">
              <div className={`h-2.5 w-2.5 rounded-full ${healthColors[p.health] ?? 'bg-gray-400'}`} />
              <span className="text-xs text-muted-foreground">{healthLabels[p.health] ?? p.health}</span>
            </div>
          )}
        </div>

        {/* Progress bar */}
        {progressPct != null && (
          <div>
            <div className="mb-1 flex justify-between text-xs text-muted-foreground">
              <span>Progress</span>
              <span>{progressPct}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-primary transition-all" style={{ width: `${progressPct}%` }} />
            </div>
          </div>
        )}

        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{p.completed_issue_count}/{p.issue_count} issues</span>
          {p.target_date && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {p.target_date}
            </span>
          )}
        </div>

        {p.url && (
          <a
            href={p.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline dark:text-blue-400"
            onClick={(e) => e.stopPropagation()}
          >
            Open in Linear <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </CardContent>
    </Card>
  )
}

function ProjectDetailPanel({ projectId }: { projectId: number }) {
  const { data, isLoading } = useProjectDetail(projectId)

  if (isLoading) return <Skeleton className="h-48 rounded-lg" />
  if (!data) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{data.name} — Issues</CardTitle>
      </CardHeader>
      <CardContent>
        {data.issues.length > 0 ? (
          <div className="max-h-96 overflow-y-auto">
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
                {data.issues.map((issue) => (
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
                      <span className="text-xs capitalize">{issue.status_category?.replace('_', ' ') ?? '—'}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs">{issue.priority_label ?? '—'}</span>
                    </TableCell>
                    <TableCell className="text-xs">{issue.estimate ?? '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No issues in this project</p>
        )}
      </CardContent>
    </Card>
  )
}
