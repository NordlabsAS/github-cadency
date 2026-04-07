import { useCallback, useRef, useState } from 'react'
import {
  CheckCircle2,
  AlertTriangle,
  Plug,
  RefreshCw,
  TestTube,
  Trash2,
  Users,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import ErrorCard from '@/components/ErrorCard'
import { timeAgo } from '@/utils/format'
import {
  useIntegrations,
  useCreateIntegration,
  useUpdateIntegration,
  useDeleteIntegration,
  useTestIntegration,
  useTriggerSync,
  useIntegrationSyncStatus,
  useLinearUsers,
  useMapUser,
  useSetPrimarySource,
} from '@/hooks/useIntegrations'
import { useDevelopers } from '@/hooks/useDevelopers'
import type { IntegrationConfig, LinearUser } from '@/utils/types'

export default function IntegrationSettings() {
  const { data: integrations, isLoading, isError, refetch } = useIntegrations()

  if (isError) return <ErrorCard message="Could not load integrations." onRetry={refetch} />

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Integrations</h1>
        <Skeleton className="h-48 w-full rounded-lg" />
      </div>
    )
  }

  const linear = integrations?.find((i) => i.type === 'linear')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Integrations</h1>
        <p className="text-sm text-muted-foreground">
          Connect external tools to enrich DevPulse with planning data
        </p>
      </div>

      {linear ? (
        <LinearIntegrationCard config={linear} />
      ) : (
        <SetupCard />
      )}
    </div>
  )
}

function SetupCard() {
  const [apiKey, setApiKey] = useState('')
  const create = useCreateIntegration()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Plug className="h-5 w-5" />
          Connect Linear
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Connect your Linear workspace to get sprint velocity, completion rates, scope creep
          tracking, triage metrics, and planning-delivery correlation.
        </p>
        <div className="max-w-md space-y-2">
          <Label htmlFor="api-key">API Key</Label>
          <Input
            id="api-key"
            type="password"
            placeholder="lin_api_..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Generate a read-only API key in Linear Settings &rarr; API
          </p>
        </div>
        <Button
          onClick={() => create.mutate({ type: 'linear', display_name: 'Linear', api_key: apiKey })}
          disabled={!apiKey || create.isPending}
        >
          {create.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Connect
        </Button>
      </CardContent>
    </Card>
  )
}

function LinearIntegrationCard({ config }: { config: IntegrationConfig }) {
  const [apiKey, setApiKey] = useState('')
  const update = useUpdateIntegration()
  const remove = useDeleteIntegration()
  const test = useTestIntegration()
  const sync = useTriggerSync()
  const setPrimary = useSetPrimarySource()
  const { data: syncStatus } = useIntegrationSyncStatus(config.id)
  const [showMapping, setShowMapping] = useState(false)

  const saveTimer = useRef<ReturnType<typeof setTimeout>>(undefined)
  const saveApiKey = useCallback(() => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      if (apiKey) update.mutate({ id: config.id, updates: { api_key: apiKey } })
    }, 800)
  }, [apiKey, config.id, update])

  const isConnected = config.status === 'active' && config.api_key_configured

  return (
    <div className="space-y-4">
      {/* Connection status banner */}
      <Card>
        <CardContent className="flex items-center justify-between py-4">
          <div className="flex items-center gap-3">
            {isConnected ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-amber-500" />
            )}
            <div>
              <p className="font-medium">
                {isConnected
                  ? `Connected to ${config.workspace_name || 'Linear'}`
                  : 'Linear not connected'}
              </p>
              {config.last_synced_at && (
                <p className="text-xs text-muted-foreground">
                  Last synced {timeAgo(config.last_synced_at)}
                </p>
              )}
              {config.error_message && (
                <p className="text-xs text-red-500">{config.error_message}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => test.mutate(config.id)}
              disabled={test.isPending || !config.api_key_configured}
            >
              {test.isPending ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <TestTube className="mr-1 h-3 w-3" />}
              Test
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => sync.mutate(config.id)}
              disabled={sync.isPending || syncStatus?.is_syncing || !isConnected}
            >
              {(sync.isPending || syncStatus?.is_syncing) ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="mr-1 h-3 w-3" />
              )}
              {syncStatus?.is_syncing ? 'Syncing...' : 'Sync Now'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Config */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">API Key</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              type="password"
              placeholder={config.api_key_configured ? '********' : 'lin_api_...'}
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value)
                saveApiKey()
              }}
            />
            <p className="text-xs text-muted-foreground">
              {config.api_key_configured ? 'Key configured. Enter a new key to replace it.' : 'No key set.'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Sync Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Issues</span>
              <span className="font-medium">{syncStatus?.issues_synced ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Sprints</span>
              <span className="font-medium">{syncStatus?.sprints_synced ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Projects</span>
              <span className="font-medium">{syncStatus?.projects_synced ?? 0}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Primary issue source toggle */}
      <Card>
        <CardContent className="flex items-center justify-between py-4">
          <div>
            <p className="font-medium">Primary Issue Source</p>
            <p className="text-xs text-muted-foreground">
              Use Linear issues instead of GitHub Issues for issue metrics
            </p>
          </div>
          <div className="flex items-center gap-2">
            {config.is_primary_issue_source && <Badge variant="outline" className="text-emerald-600">Primary</Badge>}
            <Switch
              checked={config.is_primary_issue_source}
              onCheckedChange={(checked) => {
                if (checked) setPrimary.mutate(config.id)
              }}
              disabled={!isConnected || setPrimary.isPending}
            />
          </div>
        </CardContent>
      </Card>

      {/* Developer mapping */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4" />
              Developer Mapping
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setShowMapping(!showMapping)}>
              {showMapping ? 'Hide' : 'Show'}
            </Button>
          </div>
        </CardHeader>
        {showMapping && (
          <CardContent>
            <DeveloperMappingTable integrationId={config.id} />
          </CardContent>
        )}
      </Card>

      {/* Danger zone */}
      <Card className="border-red-200 dark:border-red-900">
        <CardContent className="flex items-center justify-between py-4">
          <div>
            <p className="font-medium text-red-600 dark:text-red-400">Remove Integration</p>
            <p className="text-xs text-muted-foreground">
              Deletes all synced data (projects, sprints, issues, links)
            </p>
          </div>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => remove.mutate(config.id)}
            disabled={remove.isPending}
          >
            <Trash2 className="mr-1 h-3 w-3" />
            Remove
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

function DeveloperMappingTable({ integrationId }: { integrationId: number }) {
  const { data, isLoading } = useLinearUsers(integrationId)
  const { data: developers } = useDevelopers()
  const mapUser = useMapUser()

  if (isLoading) return <Skeleton className="h-32 w-full" />
  if (!data?.users.length) return <p className="text-sm text-muted-foreground">No Linear users found. Run a sync first.</p>

  return (
    <div className="space-y-3">
      <div className="flex gap-4 text-sm">
        <Badge variant="outline">{data.mapped_count} mapped</Badge>
        {data.unmapped_count > 0 && (
          <Badge variant="outline" className="text-amber-600">{data.unmapped_count} unmapped</Badge>
        )}
      </div>
      <div className="max-h-80 overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Linear User</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>DevPulse Developer</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.users.map((user) => (
              <MappingRow
                key={user.id}
                user={user}
                developers={developers ?? []}
                onMap={(devId) =>
                  mapUser.mutate({
                    integrationId,
                    external_user_id: user.id,
                    developer_id: devId,
                  })
                }
              />
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

function MappingRow({
  user,
  developers,
  onMap,
}: {
  user: LinearUser
  developers: { id: number; display_name: string }[]
  onMap: (devId: number) => void
}) {
  return (
    <TableRow>
      <TableCell className="font-medium">{user.name}</TableCell>
      <TableCell className="text-muted-foreground">{user.email ?? '—'}</TableCell>
      <TableCell>
        {user.mapped_developer_id ? (
          <span className="text-emerald-600 dark:text-emerald-400">{user.mapped_developer_name}</span>
        ) : (
          <Select onValueChange={(v) => onMap(Number(v))}>
            <SelectTrigger className="h-8 w-48">
              <SelectValue placeholder="Select developer..." />
            </SelectTrigger>
            <SelectContent>
              {developers.map((d) => (
                <SelectItem key={d.id} value={String(d.id)}>{d.display_name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </TableCell>
    </TableRow>
  )
}
