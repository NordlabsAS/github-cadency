import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

function ScoreBadge({ label, value }: { label: string; value: number }) {
  const color =
    value >= 7
      ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
      : value >= 4
        ? 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30'
        : 'bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/30'

  return (
    <div className={`inline-flex flex-col items-center rounded-lg border px-3 py-2 ${color}`}>
      <span className="text-2xl font-bold">{value}</span>
      <span className="text-xs">{label}</span>
    </div>
  )
}

interface FrictionPair {
  reviewer: string
  author: string
  pattern: string
}

export default function GenericAnalysisView({ result }: { result: Record<string, unknown> }) {
  // Extract scores (keys ending in _score)
  const scores: { label: string; value: number }[] = []
  const stringLists: { label: string; items: string[] }[] = []
  const frictionPairs: FrictionPair[] = []
  const otherFields: { label: string; value: string }[] = []

  for (const [key, val] of Object.entries(result)) {
    if (key.endsWith('_score') && typeof val === 'number') {
      const label = key
        .replace(/_score$/, '')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase())
      scores.push({ label, value: val })
    } else if (key === 'friction_pairs' && Array.isArray(val)) {
      frictionPairs.push(...(val as FrictionPair[]))
    } else if (Array.isArray(val) && val.length > 0 && typeof val[0] === 'string') {
      const label = key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase())
      stringLists.push({ label, items: val as string[] })
    } else if (typeof val === 'string') {
      const label = key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase())
      otherFields.push({ label, value: val })
    }
  }

  return (
    <div className="space-y-4">
      {/* Scores */}
      {scores.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {scores.map((s) => (
            <ScoreBadge key={s.label} label={s.label} value={s.value} />
          ))}
        </div>
      )}

      {/* String fields (e.g. trend) */}
      {otherFields.length > 0 && (
        <Card>
          <CardContent className="pt-4">
            <dl className="space-y-2">
              {otherFields.map((f) => (
                <div key={f.label} className="flex gap-2 text-sm">
                  <dt className="font-medium">{f.label}:</dt>
                  <dd className="text-muted-foreground">{f.value}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>
      )}

      {/* Friction Pairs */}
      {frictionPairs.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Friction Pairs</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Reviewer</TableHead>
                  <TableHead>Author</TableHead>
                  <TableHead>Pattern</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {frictionPairs.map((fp, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-medium">{fp.reviewer}</TableCell>
                    <TableCell className="font-medium">{fp.author}</TableCell>
                    <TableCell className="text-muted-foreground">{fp.pattern}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* String Lists (observations, recommendations, etc.) */}
      {stringLists.map((sl) => (
        <Card key={sl.label}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">{sl.label}</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1.5">
              {sl.items.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground" />
                  {item}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
