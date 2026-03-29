import { useNavigate } from 'react-router-dom'
import { useWorksWith } from '@/hooks/useRelationships'
import { useDateRange } from '@/hooks/useDateRange'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { HelpCircle } from 'lucide-react'
import type { WorksWithEntry } from '@/utils/types'

const signalLabels: { key: keyof WorksWithEntry; label: string }[] = [
  { key: 'review_score', label: 'Reviews' },
  { key: 'coauthor_score', label: 'Co-repos' },
  { key: 'issue_comment_score', label: 'Issue comments' },
  { key: 'mention_score', label: 'Mentions' },
  { key: 'co_assigned_score', label: 'Co-assigned' },
]

function ScoreBar({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-24 text-muted-foreground truncate">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-primary/70"
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </div>
    </div>
  )
}

function CollaboratorCard({ entry }: { entry: WorksWithEntry }) {
  const navigate = useNavigate()

  return (
    <Card
      className="cursor-pointer hover:bg-accent/50 transition-colors"
      onClick={() => navigate(`/team/${entry.developer_id}`)}
    >
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center gap-3">
          {entry.avatar_url ? (
            <img
              src={entry.avatar_url}
              alt={entry.display_name}
              className="h-10 w-10 rounded-full"
            />
          ) : (
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-sm font-bold">
              {entry.display_name[0]}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium truncate">{entry.display_name}</p>
            <p className="text-xs text-muted-foreground">@{entry.github_username}</p>
          </div>
          {entry.team && (
            <Badge variant="outline" className="text-xs shrink-0">
              {entry.team}
            </Badge>
          )}
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{entry.interaction_count} interactions</span>
          <span className="font-medium text-foreground">
            {(entry.total_score * 100).toFixed(0)}%
          </span>
        </div>
        <div className="space-y-1">
          {signalLabels.map(({ key, label }) => (
            <ScoreBar
              key={key}
              value={entry[key] as number}
              label={label}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export default function WorksWithSection({ developerId }: { developerId: number }) {
  const { dateFrom, dateTo } = useDateRange()
  const { data, isLoading } = useWorksWith(developerId, dateFrom, dateTo)

  if (isLoading) return null
  if (!data || data.collaborators.length === 0) return null

  return (
    <div className="space-y-3">
      <h2 className="flex items-center gap-1.5 text-lg font-semibold">
        Works With
        <Tooltip>
          <TooltipTrigger className="inline-flex text-muted-foreground/60 hover:text-muted-foreground transition-colors">
            <HelpCircle className="h-4 w-4" />
          </TooltipTrigger>
          <TooltipContent>
            Top collaborators based on PR reviews, co-authored repos, issue discussions, @mentions, and co-assigned issues.
          </TooltipContent>
        </Tooltip>
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {data.collaborators.slice(0, 8).map((entry) => (
          <CollaboratorCard key={entry.developer_id} entry={entry} />
        ))}
      </div>
    </div>
  )
}
