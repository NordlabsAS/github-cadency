import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useDevelopers, useCreateDeveloper, useUpdateDeveloper } from '@/hooks/useDevelopers'
import { useSyncContributors, useSyncStatus } from '@/hooks/useSync'
import ErrorCard from '@/components/ErrorCard'
import TableSkeleton from '@/components/TableSkeleton'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { CheckCircle2, RefreshCw, XCircle, Users } from 'lucide-react'
import type { Developer, DeveloperCreate } from '@/utils/types'

const ROLES = ['developer', 'senior_developer', 'lead', 'architect', 'devops', 'qa', 'intern']

function DeveloperForm({
  initial,
  onSubmit,
  submitLabel,
}: {
  initial?: Partial<DeveloperCreate>
  onSubmit: (data: DeveloperCreate) => void
  submitLabel: string
}) {
  const [form, setForm] = useState<DeveloperCreate>({
    github_username: initial?.github_username ?? '',
    display_name: initial?.display_name ?? '',
    email: initial?.email ?? '',
    role: initial?.role ?? '',
    team: initial?.team ?? '',
    skills: initial?.skills ?? [],
    specialty: initial?.specialty ?? '',
    location: initial?.location ?? '',
    timezone: initial?.timezone ?? '',
  })

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit(form)
      }}
    >
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="github_username">GitHub Username *</Label>
          <Input
            id="github_username"
            value={form.github_username}
            onChange={(e) => setForm({ ...form, github_username: e.target.value })}
            required
            disabled={!!initial?.github_username}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="display_name">Display Name *</Label>
          <Input
            id="display_name"
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={form.email ?? ''}
            onChange={(e) => setForm({ ...form, email: e.target.value || null })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="role">Role</Label>
          <select
            id="role"
            className="flex h-9 w-full rounded-md border bg-background px-3 py-1 text-sm"
            value={form.role ?? ''}
            onChange={(e) => setForm({ ...form, role: e.target.value || null })}
          >
            <option value="">Select role...</option>
            {ROLES.map((r) => (
              <option key={r} value={r}>{r.replace('_', ' ')}</option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="team">Team</Label>
          <Input
            id="team"
            value={form.team ?? ''}
            onChange={(e) => setForm({ ...form, team: e.target.value || null })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="skills">Skills (comma-separated)</Label>
          <Input
            id="skills"
            value={(form.skills ?? []).join(', ')}
            onChange={(e) =>
              setForm({
                ...form,
                skills: e.target.value
                  .split(',')
                  .map((s) => s.trim())
                  .filter(Boolean),
              })
            }
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="location">Location</Label>
          <Input
            id="location"
            value={form.location ?? ''}
            onChange={(e) => setForm({ ...form, location: e.target.value || null })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="timezone">Timezone</Label>
          <Input
            id="timezone"
            placeholder="e.g. Europe/Oslo"
            value={form.timezone ?? ''}
            onChange={(e) => setForm({ ...form, timezone: e.target.value || null })}
          />
        </div>
      </div>
      <div className="flex justify-end gap-2">
        <DialogClose asChild>
          <Button variant="outline">Cancel</Button>
        </DialogClose>
        <Button type="submit">{submitLabel}</Button>
      </div>
    </form>
  )
}

export default function TeamRegistry() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [teamFilter, setTeamFilter] = useState('')
  const { data: developers, isLoading, isError, refetch } = useDevelopers(teamFilter || undefined)
  const createDev = useCreateDeveloper()
  const syncContributors = useSyncContributors()
  const { data: syncStatus } = useSyncStatus()
  const [editDev, setEditDev] = useState<Developer | null>(null)
  const updateDev = useUpdateDeveloper(editDev?.id ?? 0)
  const [addOpen, setAddOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [showResult, setShowResult] = useState(false)

  const activeContributorSync =
    syncStatus?.active_sync?.sync_type === 'contributors' ? syncStatus.active_sync : null
  const anySyncActive = !!syncStatus?.active_sync

  // Refresh developer list and show completion banner when contributor sync finishes
  const wasActiveRef = useRef(false)
  useEffect(() => {
    if (wasActiveRef.current && !activeContributorSync) {
      qc.invalidateQueries({ queryKey: ['developers'] })
      setShowResult(true)
      const timer = setTimeout(() => setShowResult(false), 10_000)
      wasActiveRef.current = false
      return () => clearTimeout(timer)
    }
    wasActiveRef.current = !!activeContributorSync
  }, [activeContributorSync, qc])

  const lastCompleted = syncStatus?.last_completed

  const teams = [...new Set((developers ?? []).map((d) => d.team).filter(Boolean))] as string[]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Team Registry</h1>
        <div className="flex items-center gap-3">
          <select
            className="rounded-md border bg-background px-3 py-1.5 text-sm"
            value={teamFilter}
            onChange={(e) => setTeamFilter(e.target.value)}
          >
            <option value="">All teams</option>
            {teams.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>

          <Button
            variant="outline"
            onClick={() => syncContributors.mutate()}
            disabled={syncContributors.isPending || anySyncActive}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${syncContributors.isPending || activeContributorSync ? 'animate-spin' : ''}`} />
            Sync Contributors
          </Button>

          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger asChild>
              <Button>Add Developer</Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Add Developer</DialogTitle>
              </DialogHeader>
              <DeveloperForm
                submitLabel="Create"
                onSubmit={(data) => {
                  createDev.mutate(data, { onSuccess: () => setAddOpen(false) })
                }}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Active contributor sync banner */}
      {activeContributorSync && (
        <div className="flex items-center gap-3 rounded-lg border border-primary/20 bg-primary/5 px-4 py-3">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
          </span>
          <Users className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">Syncing contributors...</span>
          {(activeContributorSync.repos_synced ?? 0) > 0 && (
            <Badge variant="secondary">
              {activeContributorSync.repos_synced} new
            </Badge>
          )}
          <span className="ml-auto text-xs text-muted-foreground">
            {(activeContributorSync.log_summary ?? []).slice(-1)[0]?.msg ?? 'Starting...'}
          </span>
        </div>
      )}

      {/* Completion result banner (fades after 10s) */}
      {!activeContributorSync && showResult && lastCompleted?.sync_type === 'contributors' && (
        <div className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${
          lastCompleted.status === 'completed'
            ? 'border-emerald-500/20 bg-emerald-500/5'
            : 'border-red-500/20 bg-red-500/5'
        }`}>
          {lastCompleted.status === 'completed' ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          ) : (
            <XCircle className="h-4 w-4 text-red-600" />
          )}
          <span className="text-sm">
            {lastCompleted.status === 'completed'
              ? `Contributor sync complete${lastCompleted.repos_synced ? ` — ${lastCompleted.repos_synced} new developers added` : ''}`
              : 'Contributor sync failed'}
          </span>
        </div>
      )}

      {isError ? (
        <ErrorCard message="Could not load developers." onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton columns={8} rows={5} headers={['Name', 'GitHub', 'Role', 'Team', 'Skills', 'Location', 'Timezone', '']} />
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>GitHub</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Team</TableHead>
                <TableHead>Skills</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Timezone</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {(developers ?? []).map((dev) => (
                <TableRow
                  key={dev.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/team/${dev.id}`)}
                >
                  <TableCell className="font-medium">{dev.display_name}</TableCell>
                  <TableCell className="text-muted-foreground">{dev.github_username}</TableCell>
                  <TableCell>
                    {dev.role && (
                      <Badge variant="secondary">{dev.role.replace('_', ' ')}</Badge>
                    )}
                  </TableCell>
                  <TableCell>{dev.team}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {(dev.skills ?? []).slice(0, 3).map((s) => (
                        <Badge key={s} variant="outline" className="text-xs">{s}</Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{dev.location}</TableCell>
                  <TableCell className="text-muted-foreground">{dev.timezone}</TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        setEditDev(dev)
                        setEditOpen(true)
                      }}
                    >
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {(developers ?? []).length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground">
                    No developers found. Add one to get started.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Developer</DialogTitle>
          </DialogHeader>
          {editDev && (
            <DeveloperForm
              initial={editDev}
              submitLabel="Save"
              onSubmit={({ github_username, ...updateData }) => {
                void github_username
                updateDev.mutate(updateData, { onSuccess: () => setEditOpen(false) })
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
