import { useState } from 'react'
import { useCreateSelfGoal, useCreateAdminGoal } from '@/hooks/useGoals'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from '@/components/ui/dialog'
import type { GoalMetricKey, Developer } from '@/utils/types'

export const metricKeyLabels: Record<string, string> = {
  prs_merged: 'PRs Merged',
  prs_opened: 'PRs Opened',
  time_to_merge_h: 'Time to Merge (h)',
  time_to_first_review_h: 'Time to First Review (h)',
  reviews_given: 'Reviews Given',
  review_quality_score: 'Review Quality Score',
  issues_closed: 'Issues Closed',
  avg_pr_additions: 'Avg PR Additions',
}

interface GoalCreateDialogProps {
  /** Pre-selected developer (used from DeveloperDetail) */
  developerId?: number
  /** List of developers for admin dropdown (used from Goals page) */
  developers?: Developer[]
  isAdmin: boolean
  /** Whether the current user is viewing their own page */
  isOwnPage: boolean
  trigger?: React.ReactNode
}

export default function GoalCreateDialog({
  developerId,
  developers,
  isAdmin,
  isOwnPage,
  trigger,
}: GoalCreateDialogProps) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [metric, setMetric] = useState<GoalMetricKey>('prs_merged')
  const [target, setTarget] = useState('')
  const [direction, setDirection] = useState<'above' | 'below'>('above')
  const [date, setDate] = useState('')
  const [selectedDevId, setSelectedDevId] = useState<string>(
    developerId ? String(developerId) : ''
  )

  const createSelfGoal = useCreateSelfGoal()
  const createAdminGoal = useCreateAdminGoal()

  const reset = () => {
    setTitle('')
    setTarget('')
    setDate('')
    setMetric('prs_merged')
    setDirection('above')
    if (!developerId) setSelectedDevId('')
  }

  const handleSubmit = () => {
    const payload = {
      title,
      metric_key: metric,
      target_value: Number(target),
      target_direction: direction,
      target_date: date || undefined,
    }
    const onSuccess = () => setOpen(false)

    const targetDevId = developerId ?? Number(selectedDevId)

    if (isAdmin && !isOwnPage) {
      createAdminGoal.mutate(
        { ...payload, developer_id: targetDevId },
        { onSuccess }
      )
    } else {
      createSelfGoal.mutate(payload, { onSuccess })
    }
  }

  const isPending = createSelfGoal.isPending || createAdminGoal.isPending
  const showDevSelector = isAdmin && !developerId && developers && developers.length > 0
  const targetNum = Number(target)
  const canSubmit = title && target && !isNaN(targetNum) && targetNum > 0 && (!showDevSelector || selectedDevId)

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset() }}>
      <DialogTrigger>
        {trigger ?? <Button variant="outline" size="sm">Add Goal</Button>}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Goal</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {showDevSelector && (
            <div className="space-y-1.5">
              <Label>Developer</Label>
              <Select value={selectedDevId} onValueChange={(v) => v && setSelectedDevId(v)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select developer" />
                </SelectTrigger>
                <SelectContent>
                  {developers.map((d) => (
                    <SelectItem key={d.id} value={String(d.id)}>
                      {d.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="space-y-1.5">
            <Label>Title</Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Improve review quality"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Metric</Label>
            <Select value={metric} onValueChange={(v) => setMetric(v as GoalMetricKey)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(metricKeyLabels).map(([key, label]) => (
                  <SelectItem key={key} value={key}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Target Value</Label>
              <Input
                type="number"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="e.g. 10"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Direction</Label>
              <Select value={direction} onValueChange={(v) => setDirection(v as 'above' | 'below')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="above">Above</SelectItem>
                  <SelectItem value="below">Below</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Target Date (optional)</Label>
            <Input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2">
            <DialogClose>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button disabled={!canSubmit || isPending} onClick={handleSubmit}>
              {isPending ? 'Creating...' : 'Create'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
