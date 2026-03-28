import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { ReviewQualityBreakdown } from '@/utils/types'

interface ReviewQualityDonutProps {
  breakdown: ReviewQualityBreakdown
  score: number | null | undefined
}

const tiers = [
  { key: 'thorough', label: 'Thorough', color: '#22c55e' },
  { key: 'standard', label: 'Standard', color: '#3b82f6' },
  { key: 'minimal', label: 'Minimal', color: '#f59e0b' },
  { key: 'rubber_stamp', label: 'Rubber Stamp', color: '#94a3b8' },
] as const

export default function ReviewQualityDonut({
  breakdown,
  score,
}: ReviewQualityDonutProps) {
  const data = tiers
    .map((t) => ({ name: t.label, value: breakdown[t.key], color: t.color }))
    .filter((d) => d.value > 0)

  const total = data.reduce((sum, d) => sum + d.value, 0)

  if (total === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Review Quality
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No review data available.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Review Quality
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
              >
                {data.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
                formatter={(value: number, name: string) => [
                  `${value} (${((value / total) * 100).toFixed(0)}%)`,
                  name,
                ]}
              />
            </PieChart>
          </ResponsiveContainer>
          {/* Center score */}
          {score != null && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-center">
                <div className="text-2xl font-bold">{score.toFixed(1)}</div>
                <div className="text-[10px] text-muted-foreground">/ 10</div>
              </div>
            </div>
          )}
        </div>
        {/* Legend */}
        <div className="mt-2 flex flex-wrap justify-center gap-3">
          {data.map((d) => (
            <div key={d.name} className="flex items-center gap-1.5 text-xs">
              <div
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: d.color }}
              />
              <span className="text-muted-foreground">
                {d.name} ({d.value})
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
