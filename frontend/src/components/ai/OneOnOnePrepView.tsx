import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from '@/components/ui/accordion'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ExternalLink } from 'lucide-react'

interface MetricHighlight {
  metric: string
  value: string
  context: string
  concern_level: 'none' | 'low' | 'moderate' | 'high'
}

interface TalkingPoint {
  topic: string
  framing: string
  evidence: string
}

interface GoalProgress {
  title: string
  status: string
  current_value: string
}

interface NotableWorkItem {
  description?: string
  number?: number
  title?: string
  url?: string
}

interface OneOnOnePrepResult {
  period_summary: string
  metrics_highlights: MetricHighlight[]
  notable_work: (string | NotableWorkItem)[]
  suggested_talking_points: TalkingPoint[]
  goal_progress: GoalProgress[]
}

const concernColors: Record<string, string> = {
  none: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400',
  low: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400',
  moderate: 'bg-amber-500/15 text-amber-700 dark:text-amber-400',
  high: 'bg-red-500/15 text-red-700 dark:text-red-400',
}

function ConcernBadge({ level }: { level: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${concernColors[level] ?? concernColors.none}`}
    >
      {level}
    </span>
  )
}

function ProgressBar({ label, status, value }: { label: string; status: string; value: string }) {
  const pct = parseFloat(value)
  const width = !isNaN(pct) ? Math.min(Math.max(pct, 0), 100) : null

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">{status}</span>
      </div>
      {width !== null ? (
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${width}%` }}
          />
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">{value}</p>
      )}
    </div>
  )
}

export default function OneOnOnePrepView({ result }: { result: Record<string, unknown> }) {
  const data = result as unknown as OneOnOnePrepResult

  return (
    <div className="space-y-4">
      {/* Period Summary */}
      {data.period_summary && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Period Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed">{data.period_summary}</p>
          </CardContent>
        </Card>
      )}

      {/* Metrics Highlights */}
      {data.metrics_highlights && data.metrics_highlights.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Metrics Highlights</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Metric</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Context</TableHead>
                  <TableHead>Concern</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.metrics_highlights.map((m, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-medium">{m.metric}</TableCell>
                    <TableCell>{m.value}</TableCell>
                    <TableCell className="text-muted-foreground">{m.context}</TableCell>
                    <TableCell>
                      <ConcernBadge level={m.concern_level} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Notable Work */}
      {data.notable_work && data.notable_work.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Notable Work</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.notable_work.map((item, i) => {
                if (typeof item === 'string') {
                  return (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                      {item}
                    </li>
                  )
                }
                const work = item as NotableWorkItem
                return (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    <span>
                      {work.title ?? work.description}
                      {work.number && <span className="text-muted-foreground"> #{work.number}</span>}
                      {work.url && (
                        <a
                          href={work.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-1 inline-flex items-center text-primary hover:underline"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </span>
                  </li>
                )
              })}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Suggested Talking Points */}
      {data.suggested_talking_points && data.suggested_talking_points.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Suggested Talking Points</CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion>
              {data.suggested_talking_points.map((tp, i) => (
                <AccordionItem key={i} value={i}>
                  <AccordionTrigger className="text-sm">
                    {tp.topic}
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-2 pl-1">
                      <p className="text-sm">{tp.framing}</p>
                      {tp.evidence && (
                        <p className="text-xs text-muted-foreground">
                          <span className="font-medium">Evidence:</span> {tp.evidence}
                        </p>
                      )}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </CardContent>
        </Card>
      )}

      {/* Goal Progress */}
      {data.goal_progress && data.goal_progress.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Goal Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.goal_progress.map((g, i) => (
              <ProgressBar key={i} label={g.title} status={g.status} value={g.current_value} />
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
