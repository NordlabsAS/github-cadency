import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useRelationships,
  useCreateRelationship,
  useDeleteRelationship,
} from '@/hooks/useRelationships'
import { useDevelopers } from '@/hooks/useDevelopers'
import { useAuth } from '@/hooks/useAuth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Users, X, Plus } from 'lucide-react'
import type { RelationshipType, DeveloperRelationshipResponse } from '@/utils/types'

const RELATIONSHIP_LABELS: Record<RelationshipType, string> = {
  reports_to: 'Reports to',
  tech_lead_of: 'Tech Lead',
  team_lead_of: 'Team Lead',
}

function RelLink({
  rel,
  developerId,
  onRemove,
  isAdmin,
}: {
  rel: DeveloperRelationshipResponse
  developerId: number
  onRemove?: () => void
  isAdmin: boolean
}) {
  const navigate = useNavigate()
  const otherId = rel.source_id === developerId ? rel.target_id : rel.source_id
  const otherName = rel.source_id === developerId ? rel.target_name : rel.source_name
  const otherAvatar = rel.source_id === developerId ? rel.target_avatar_url : rel.source_avatar_url

  return (
    <div className="flex items-center gap-2 group">
      <button
        className="flex items-center gap-2 hover:text-primary transition-colors text-sm"
        onClick={() => navigate(`/team/${otherId}`)}
      >
        {otherAvatar ? (
          <img src={otherAvatar} className="h-6 w-6 rounded-full" alt="" />
        ) : (
          <div className="h-6 w-6 rounded-full bg-muted flex items-center justify-center text-xs font-bold">
            {otherName[0]}
          </div>
        )}
        <span className="font-medium">{otherName}</span>
      </button>
      {isAdmin && onRemove && (
        <button
          className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-all"
          onClick={onRemove}
          title="Remove"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  )
}

function AddRelationshipDialog({
  developerId,
  relationshipType,
  label,
}: {
  developerId: number
  relationshipType: RelationshipType
  label: string
}) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const { data: developers } = useDevelopers()
  const createRel = useCreateRelationship(developerId)

  const filtered = (developers ?? []).filter(
    (d) =>
      d.id !== developerId &&
      d.is_active &&
      (d.display_name.toLowerCase().includes(search.toLowerCase()) ||
        d.github_username.toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 text-xs gap-1">
          <Plus className="h-3 w-3" />
          Set {label}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Set {label}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label>Search developer</Label>
            <input
              className="flex h-9 w-full rounded-md border bg-background px-3 py-1 text-sm"
              placeholder="Type name or username..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>
          <div className="max-h-48 overflow-y-auto space-y-1">
            {filtered.slice(0, 20).map((dev) => (
              <button
                key={dev.id}
                className="flex items-center gap-2 w-full rounded-md px-2 py-1.5 text-sm hover:bg-accent transition-colors"
                onClick={() => {
                  createRel.mutate(
                    { target_id: dev.id, relationship_type: relationshipType },
                    { onSuccess: () => setOpen(false) }
                  )
                }}
              >
                {dev.avatar_url ? (
                  <img src={dev.avatar_url} className="h-6 w-6 rounded-full" alt="" />
                ) : (
                  <div className="h-6 w-6 rounded-full bg-muted flex items-center justify-center text-xs font-bold">
                    {dev.display_name[0]}
                  </div>
                )}
                <span>{dev.display_name}</span>
                <span className="text-muted-foreground ml-auto text-xs">@{dev.github_username}</span>
              </button>
            ))}
            {filtered.length === 0 && (
              <p className="text-sm text-muted-foreground py-2 text-center">No developers found</p>
            )}
          </div>
          <DialogClose asChild>
            <Button variant="outline" className="w-full">Cancel</Button>
          </DialogClose>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default function RelationshipsCard({ developerId }: { developerId: number }) {
  const { data: rels, isLoading } = useRelationships(developerId)
  const deleteRel = useDeleteRelationship(developerId)
  const { isAdmin } = useAuth()

  if (isLoading || !rels) return null

  const hasAny =
    rels.reports_to ||
    rels.tech_lead ||
    rels.team_lead ||
    rels.direct_reports.length > 0 ||
    rels.tech_leads_for.length > 0 ||
    rels.team_leads_for.length > 0

  if (!hasAny && !isAdmin) return null

  const rows: {
    label: string
    type: RelationshipType
    rel: DeveloperRelationshipResponse | null
  }[] = [
    { label: 'Reports to', type: 'reports_to', rel: rels.reports_to },
    { label: 'Tech Lead', type: 'tech_lead_of', rel: rels.tech_lead },
    { label: 'Team Lead', type: 'team_lead_of', rel: rels.team_lead },
  ]

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Users className="h-4 w-4" />
          Relationships
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {rows.map(({ label, type, rel }) => (
          <div key={type} className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground w-24">{label}</span>
            {rel ? (
              <RelLink
                rel={rel}
                developerId={developerId}
                isAdmin={isAdmin}
                onRemove={() =>
                  deleteRel.mutate({
                    target_id: rel.target_id,
                    relationship_type: type,
                  })
                }
              />
            ) : isAdmin ? (
              <AddRelationshipDialog
                developerId={developerId}
                relationshipType={type}
                label={label}
              />
            ) : (
              <span className="text-sm text-muted-foreground">-</span>
            )}
          </div>
        ))}

        {rels.direct_reports.length > 0 && (
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground mb-2">
              Direct Reports ({rels.direct_reports.length})
            </p>
            <div className="space-y-1.5">
              {rels.direct_reports.map((r) => (
                <RelLink
                  key={r.id}
                  rel={r}
                  developerId={developerId}
                  isAdmin={isAdmin}
                />
              ))}
            </div>
          </div>
        )}

        {rels.tech_leads_for.length > 0 && (
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground mb-2">
              Tech Lead for ({rels.tech_leads_for.length})
            </p>
            <div className="space-y-1.5">
              {rels.tech_leads_for.map((r) => (
                <RelLink
                  key={r.id}
                  rel={r}
                  developerId={developerId}
                  isAdmin={isAdmin}
                />
              ))}
            </div>
          </div>
        )}

        {rels.team_leads_for.length > 0 && (
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground mb-2">
              Team Lead for ({rels.team_leads_for.length})
            </p>
            <div className="space-y-1.5">
              {rels.team_leads_for.map((r) => (
                <RelLink
                  key={r.id}
                  rel={r}
                  developerId={developerId}
                  isAdmin={isAdmin}
                />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
