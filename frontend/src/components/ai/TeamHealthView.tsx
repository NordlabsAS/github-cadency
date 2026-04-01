import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface WorkloadConcern {
  concern: string
  suggestion: string
}

interface CommunicationFlag {
  severity: 'low' | 'medium' | 'high'
  observation: string
}

interface ActionItem {
  priority: 'high' | 'medium' | 'low'
  action: string
  owner: string
}

interface TeamHealthResult {
  overall_health_score: number | string
  velocity_assessment: string
  workload_concerns: WorkloadConcern[]
  collaboration_patterns: string
  communication_flags: CommunicationFlag[]
  process_recommendations: string[]
  strengths: string[]
  action_items: ActionItem[]
}

function HealthScore({ score }: { score: number }) {
  const color =
    score >= 7
      ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
      : score >= 4
        ? 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30'
        : 'bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/30'

  return (
    <div className={`inline-flex items-center gap-2 rounded-lg border px-4 py-2 ${color}`}>
      <span className="text-3xl font-bold">{score}</span>
      <span className="text-sm font-medium">/10</span>
    </div>
  )
}

const severityColors: Record<string, string> = {
  low: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400',
  medium: 'bg-amber-500/15 text-amber-700 dark:text-amber-400',
  high: 'bg-red-500/15 text-red-700 dark:text-red-400',
}

const priorityColors: Record<string, string> = {
  low: 'bg-muted text-muted-foreground',
  medium: 'bg-amber-500/15 text-amber-700 dark:text-amber-400',
  high: 'bg-red-500/15 text-red-700 dark:text-red-400',
}

export default function TeamHealthView({ result }: { result: Record<string, unknown> }) {
  const data = result as unknown as TeamHealthResult
  const score = typeof data.overall_health_score === 'string'
    ? parseInt(data.overall_health_score, 10)
    : data.overall_health_score

  return (
    <div className="space-y-4">
      {/* Health Score + Velocity */}
      <Card>
        <CardContent className="flex items-start gap-6 pt-6">
          {!isNaN(score) && <HealthScore score={score} />}
          {data.velocity_assessment && (
            <div className="flex-1 space-y-1">
              <p className="text-sm font-medium">Velocity Assessment</p>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {data.velocity_assessment}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Strengths */}
      {data.strengths && data.strengths.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Strengths</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.strengths.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                  {s}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Workload Concerns */}
      {data.workload_concerns && data.workload_concerns.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Workload Concerns</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.workload_concerns.map((wc, i) => (
              <div key={i} className="rounded-md border border-amber-500/20 bg-amber-500/5 p-3">
                <p className="text-sm font-medium">{wc.concern}</p>
                <p className="mt-1 text-xs text-muted-foreground">{wc.suggestion}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Collaboration Patterns */}
      {data.collaboration_patterns && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Collaboration Patterns</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed">{data.collaboration_patterns}</p>
          </CardContent>
        </Card>
      )}

      {/* Communication Flags */}
      {data.communication_flags && data.communication_flags.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Communication Flags</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.communication_flags.map((cf, i) => (
              <div key={i} className="flex items-start gap-2">
                <span
                  className={`mt-0.5 inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium ${severityColors[cf.severity] ?? severityColors.low}`}
                >
                  {cf.severity}
                </span>
                <p className="text-sm">{cf.observation}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Process Recommendations */}
      {data.process_recommendations && data.process_recommendations.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Process Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="list-inside list-decimal space-y-1.5 text-sm">
              {data.process_recommendations.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}

      {/* Action Items */}
      {data.action_items && data.action_items.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Action Items</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-24">Priority</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead className="w-28">Owner</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.action_items.map((ai, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${priorityColors[ai.priority] ?? priorityColors.low}`}
                      >
                        {ai.priority}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm">{ai.action}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{ai.owner}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
