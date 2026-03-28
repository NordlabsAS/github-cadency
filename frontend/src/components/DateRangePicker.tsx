import { useState } from 'react'
import { format, parse, startOfQuarter, subDays } from 'date-fns'
import { CalendarIcon } from 'lucide-react'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const DATE_FMT = 'yyyy-MM-dd'

const presets = [
  { label: '7d', days: 7 },
  { label: '14d', days: 14 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
] as const

function daysAgo(days: number): string {
  return format(subDays(new Date(), days), DATE_FMT)
}

function today(): string {
  return format(new Date(), DATE_FMT)
}

function thisQuarterStart(): string {
  return format(startOfQuarter(new Date()), DATE_FMT)
}

function toDate(s: string): Date {
  return parse(s, DATE_FMT, new Date())
}

interface DateRangePickerProps {
  dateFrom: string
  dateTo: string
  onDateFromChange: (v: string) => void
  onDateToChange: (v: string) => void
}

export default function DateRangePicker({
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
}: DateRangePickerProps) {
  const [open, setOpen] = useState(false)

  const isPresetActive = (days: number) =>
    dateFrom === daysAgo(days) && dateTo === today()

  const isQuarterActive =
    dateFrom === thisQuarterStart() && dateTo === today()

  const applyPreset = (days: number) => {
    onDateFromChange(daysAgo(days))
    onDateToChange(today())
  }

  const applyQuarter = () => {
    onDateFromChange(thisQuarterStart())
    onDateToChange(today())
  }

  return (
    <div className="flex items-center gap-1.5">
      {presets.map((p) => (
        <button
          key={p.label}
          type="button"
          onClick={() => applyPreset(p.days)}
          className={cn(
            'rounded-md px-2 py-1 text-xs font-medium transition-colors',
            isPresetActive(p.days)
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
          )}
        >
          {p.label}
        </button>
      ))}
      <button
        type="button"
        onClick={applyQuarter}
        className={cn(
          'rounded-md px-2 py-1 text-xs font-medium transition-colors',
          isQuarterActive
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
        )}
      >
        Quarter
      </button>

      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          render={
            <Button
              variant="outline"
              size="sm"
              className="ml-1 gap-1.5 text-xs font-normal"
            />
          }
        >
          <CalendarIcon className="size-3.5" />
          <span>
            {format(toDate(dateFrom), 'MMM d')} &ndash; {format(toDate(dateTo), 'MMM d')}
          </span>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0">
          <div className="flex">
            <div className="border-r p-3">
              <p className="mb-2 text-xs font-medium text-muted-foreground">From</p>
              <Calendar
                mode="single"
                selected={toDate(dateFrom)}
                onSelect={(d) => {
                  if (d) onDateFromChange(format(d, DATE_FMT))
                }}
                defaultMonth={toDate(dateFrom)}
              />
            </div>
            <div className="p-3">
              <p className="mb-2 text-xs font-medium text-muted-foreground">To</p>
              <Calendar
                mode="single"
                selected={toDate(dateTo)}
                onSelect={(d) => {
                  if (d) onDateToChange(format(d, DATE_FMT))
                }}
                defaultMonth={toDate(dateTo)}
              />
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}
