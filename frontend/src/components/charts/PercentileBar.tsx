import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { PercentilePlacement } from '@/utils/types'

interface PercentileBarProps {
  label: string
  placement: PercentilePlacement
  lowerIsBetter?: boolean
  formatValue?: (v: number) => string
}

const bandLabels: Record<string, string> = {
  below_p25: 'Bottom 25%',
  p25_to_p50: '25th–50th',
  p50_to_p75: '50th–75th',
  above_p75: 'Top 25%',
}

export default function PercentileBar({
  label,
  placement,
  lowerIsBetter = false,
  formatValue = (v) => String(v),
}: PercentileBarProps) {
  const { value, percentile_band, team_median } = placement

  // Map band to a 0-100 position for the marker
  const bandPositions: Record<string, number> = {
    below_p25: 12.5,
    p25_to_p50: 37.5,
    p50_to_p75: 62.5,
    above_p75: 87.5,
  }
  const markerPos = bandPositions[percentile_band] ?? 50

  // Color logic: above_p75 is best unless lowerIsBetter
  const bandColors = lowerIsBetter
    ? { below_p25: 'bg-emerald-500', p25_to_p50: 'bg-emerald-300', p50_to_p75: 'bg-amber-300', above_p75: 'bg-red-400' }
    : { below_p25: 'bg-red-400', p25_to_p50: 'bg-amber-300', p50_to_p75: 'bg-emerald-300', above_p75: 'bg-emerald-500' }

  const activeBandColor = bandColors[percentile_band as keyof typeof bandColors] ?? 'bg-muted'

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-baseline justify-between">
          <span className="text-lg font-semibold">{formatValue(value)}</span>
          <span className="text-xs text-muted-foreground">
            Median: {formatValue(team_median)}
          </span>
        </div>
        {/* Bar with 4 zones */}
        <div className="relative h-3 flex rounded-full overflow-hidden">
          {(['below_p25', 'p25_to_p50', 'p50_to_p75', 'above_p75'] as const).map((band) => (
            <div
              key={band}
              className={`flex-1 ${
                band === percentile_band
                  ? activeBandColor
                  : 'bg-muted'
              }`}
            />
          ))}
          {/* Marker */}
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-5 w-1.5 rounded-full bg-foreground ring-2 ring-background"
            style={{ left: `${markerPos}%` }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-muted-foreground">
          <span>p25</span>
          <span>p50</span>
          <span>p75</span>
        </div>
        <p className="text-xs text-muted-foreground text-center">
          {bandLabels[percentile_band] ?? percentile_band}
        </p>
      </CardContent>
    </Card>
  )
}
