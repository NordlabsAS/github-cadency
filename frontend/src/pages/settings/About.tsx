import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import ErrorCard from '@/components/ErrorCard'
import { useVersion } from '@/hooks/useVersion'
import { Info } from 'lucide-react'

export default function About() {
  const { data, isLoading, error } = useVersion()

  if (error) return <ErrorCard title="Failed to load version info" error={error} />

  const clientVersion = import.meta.env.VITE_DEVPULSE_VERSION || 'dev'
  const clientBuild = import.meta.env.VITE_DEVPULSE_BUILD_NUMBER || '0'
  const clientCommit = import.meta.env.VITE_DEVPULSE_COMMIT_SHA || 'local'

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">About</h2>
        <p className="text-muted-foreground">Version and build information</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Info className="h-5 w-5" />
            Backend
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-5 w-64" />
              ))}
            </div>
          ) : data ? (
            <dl className="grid grid-cols-[140px_1fr] gap-y-2 text-sm">
              <dt className="text-muted-foreground">Version</dt>
              <dd className="font-mono">{data.full_version}</dd>
              <dt className="text-muted-foreground">Commit</dt>
              <dd className="font-mono">{data.commit}</dd>
              <dt className="text-muted-foreground">Deployed</dt>
              <dd className="font-mono">{data.deployed_at === 'unknown' ? 'N/A' : data.deployed_at}</dd>
            </dl>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Info className="h-5 w-5" />
            Frontend
          </CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-[140px_1fr] gap-y-2 text-sm">
            <dt className="text-muted-foreground">Version</dt>
            <dd className="font-mono">
              {clientVersion}{clientBuild !== '0' ? `+build.${clientBuild}` : ''}
            </dd>
            <dt className="text-muted-foreground">Commit</dt>
            <dd className="font-mono">{clientCommit}</dd>
          </dl>
        </CardContent>
      </Card>
    </div>
  )
}
