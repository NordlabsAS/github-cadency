import { LineChart, Line, ReferenceLine, ResponsiveContainer } from 'recharts'
import type { GoalProgressPoint } from '@/utils/types'

interface GoalSparklineProps {
  history: GoalProgressPoint[]
  targetValue: number
}

export default function GoalSparkline({ history, targetValue }: GoalSparklineProps) {
  const data = history.map((p) => ({ value: p.value }))

  return (
    <ResponsiveContainer width={120} height={32}>
      <LineChart data={data} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
        <Line
          type="monotone"
          dataKey="value"
          stroke="hsl(var(--primary))"
          strokeWidth={1.5}
          dot={false}
        />
        <ReferenceLine
          y={targetValue}
          stroke="hsl(var(--muted-foreground))"
          strokeDasharray="3 3"
          strokeWidth={1}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
