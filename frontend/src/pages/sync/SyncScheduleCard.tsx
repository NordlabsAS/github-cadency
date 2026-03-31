import { useCallback, useEffect, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { CalendarClock } from 'lucide-react'
import { useSyncSchedule, useUpdateSyncSchedule } from '@/hooks/useSync'

export default function SyncScheduleCard() {
  const { data: schedule, isLoading } = useSyncSchedule()
  const updateSchedule = useUpdateSyncSchedule()

  const [enabled, setEnabled] = useState(true)
  const [interval, setInterval_] = useState(15)
  const [cronHour, setCronHour] = useState(2)
  const initialized = useRef(false)

  // Sync local state from server data
  useEffect(() => {
    if (schedule && !initialized.current) {
      initialized.current = true
      setEnabled(schedule.auto_sync_enabled)
      setInterval_(schedule.incremental_interval_minutes)
      setCronHour(schedule.full_sync_cron_hour)
    }
  }, [schedule])

  // Debounced save for numeric inputs
  const saveTimer = useRef<ReturnType<typeof setTimeout>>()
  const debouncedSave = useCallback((data: Record<string, unknown>) => {
    clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      updateSchedule.mutate(data)
    }, 800)
  }, [updateSchedule])

  const handleToggle = (checked: boolean) => {
    setEnabled(checked)
    updateSchedule.mutate({ auto_sync_enabled: checked })
  }

  const handleIntervalChange = (value: string) => {
    const num = parseInt(value, 10)
    if (isNaN(num)) return
    setInterval_(num)
    if (num >= 5) {
      debouncedSave({ incremental_interval_minutes: num })
    }
  }

  const handleCronHourChange = (value: string) => {
    const num = parseInt(value, 10)
    if (isNaN(num)) return
    setCronHour(num)
    if (num >= 0 && num <= 23) {
      debouncedSave({ full_sync_cron_hour: num })
    }
  }

  if (isLoading) {
    return <div className="h-48 animate-pulse rounded-xl bg-muted" />
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CalendarClock className="h-5 w-5 text-muted-foreground" />
          Auto-Sync Schedule
        </CardTitle>
        <CardDescription>
          Configure automatic background syncing. Changes take effect immediately.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <Label htmlFor="auto-sync-toggle" className="text-sm font-medium">Enable auto-sync</Label>
            <p className="text-xs text-muted-foreground mt-0.5">
              Automatically sync repos on a schedule
            </p>
          </div>
          <Switch
            id="auto-sync-toggle"
            checked={enabled}
            onCheckedChange={handleToggle}
          />
        </div>

        {enabled && (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="sync-interval" className="text-sm">
                  Incremental sync interval
                </Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="sync-interval"
                    type="number"
                    min={5}
                    max={1440}
                    value={interval}
                    onChange={(e) => handleIntervalChange(e.target.value)}
                    className="w-24"
                  />
                  <span className="text-sm text-muted-foreground">minutes</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Minimum 5 minutes. Fetches changes since each repo's last sync.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="full-sync-hour" className="text-sm">
                  Nightly full sync hour
                </Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="full-sync-hour"
                    type="number"
                    min={0}
                    max={23}
                    value={cronHour}
                    onChange={(e) => handleCronHourChange(e.target.value)}
                    className="w-24"
                  />
                  <span className="text-sm text-muted-foreground">:00 (server time)</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Full re-sync of all tracked repos at this hour daily.
                </p>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
