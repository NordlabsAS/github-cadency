import { useId } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { TrendPeriod, TrendDirection } from '@/utils/types'

interface TrendChartProps {
  title: string
  data: TrendPeriod[]
  metricKey: keyof TrendPeriod
  direction?: TrendDirection
  formatValue?: (v: number) => string
}

const directionConfig = {
  improving: { label: 'Improving', className: 'bg-emerald-500/10 text-emerald-600' },
  stable: { label: 'Stable', className: 'bg-muted text-muted-foreground' },
  worsening: { label: 'Worsening', className: 'bg-red-500/10 text-red-600' },
}

export default function TrendChart({
  title,
  data,
  metricKey,
  direction,
  formatValue,
}: TrendChartProps) {
  const uid = useId()

  const chartData = data.map((p) => ({
    label: new Date(p.start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    value: (p[metricKey] as number) ?? 0,
  }))

  // Compute regression line endpoints
  const n = chartData.length
  let regressionStart: number | undefined
  let regressionEnd: number | undefined
  if (n >= 2) {
    const values = chartData.map((d) => d.value)
    const meanX = (n - 1) / 2
    const meanY = values.reduce((a, b) => a + b, 0) / n
    let num = 0
    let den = 0
    for (let i = 0; i < n; i++) {
      num += (i - meanX) * (values[i] - meanY)
      den += (i - meanX) * (i - meanX)
    }
    const slope = den !== 0 ? num / den : 0
    regressionStart = meanY - slope * meanX
    regressionEnd = meanY + slope * (n - 1 - meanX)
  }

  const dir = direction ? directionConfig[direction.direction] : null

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {dir && (
          <Badge variant="secondary" className={dir.className}>
            {dir.label}
            {direction && direction.change_pct !== 0 && (
              <span className="ml-1">
                {direction.change_pct > 0 ? '+' : ''}
                {direction.change_pct.toFixed(0)}%
              </span>
            )}
          </Badge>
        )}
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id={`gradient-${metricKey}-${uid}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.2} />
                <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11 }}
              className="fill-muted-foreground"
            />
            <YAxis
              tick={{ fontSize: 11 }}
              className="fill-muted-foreground"
              tickFormatter={formatValue}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px',
                fontSize: '12px',
              }}
              formatter={((value: number) =>
                formatValue ? formatValue(value) : value
              ) as never}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="hsl(var(--primary))"
              fill={`url(#gradient-${metricKey}-${uid})`}
              strokeWidth={2}
            />
            {regressionStart !== undefined && regressionEnd !== undefined && (
              <ReferenceLine
                segment={[
                  { x: chartData[0]?.label, y: regressionStart },
                  { x: chartData[n - 1]?.label, y: regressionEnd },
                ]}
                stroke="hsl(var(--muted-foreground))"
                strokeDasharray="6 3"
                strokeWidth={1.5}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
