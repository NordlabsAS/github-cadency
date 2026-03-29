import { useMemo, useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { SyncLogEntry } from '@/utils/types'

interface SyncLogViewerProps {
  logs: SyncLogEntry[]
  autoScroll?: boolean
}

const levelColors: Record<string, string> = {
  info: 'text-muted-foreground',
  warn: 'text-amber-600',
  error: 'text-red-600',
}

type LevelFilter = 'all' | 'info' | 'warn' | 'error'

export default function SyncLogViewer({ logs, autoScroll: initialAutoScroll = false }: SyncLogViewerProps) {
  const [levelFilter, setLevelFilter] = useState<LevelFilter>('all')
  const [repoFilter, setRepoFilter] = useState<string>('all')
  const [autoScroll, setAutoScroll] = useState(initialAutoScroll)
  const scrollRef = useRef<HTMLDivElement>(null)

  const repos = useMemo(() => {
    const set = new Set<string>()
    for (const entry of logs) {
      if (entry.repo) set.add(entry.repo)
    }
    return Array.from(set).sort()
  }, [logs])

  const filtered = useMemo(() => {
    return logs.filter((entry) => {
      if (levelFilter !== 'all' && entry.level !== levelFilter) return false
      if (repoFilter !== 'all' && entry.repo !== repoFilter) return false
      return true
    })
  }, [logs, levelFilter, repoFilter])

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [filtered, autoScroll])

  if (logs.length === 0) {
    return <p className="text-sm text-muted-foreground">No log entries.</p>
  }

  return (
    <div className="space-y-2">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1">
          {(['all', 'info', 'warn', 'error'] as const).map((level) => (
            <Button
              key={level}
              variant={levelFilter === level ? 'default' : 'ghost'}
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={() => setLevelFilter(level)}
            >
              {level === 'all' ? 'All' : level.charAt(0).toUpperCase() + level.slice(1)}
            </Button>
          ))}
        </div>
        {repos.length > 1 && (
          <select
            value={repoFilter}
            onChange={(e) => setRepoFilter(e.target.value)}
            className="h-6 rounded border bg-background px-1.5 text-xs"
          >
            <option value="all">All repos</option>
            {repos.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        )}
        <Button
          variant={autoScroll ? 'secondary' : 'ghost'}
          size="sm"
          className="ml-auto h-6 px-2 text-xs"
          onClick={() => setAutoScroll(!autoScroll)}
        >
          Auto-scroll {autoScroll ? 'on' : 'off'}
        </Button>
        <span className="text-xs text-muted-foreground">
          {filtered.length}/{logs.length}
        </span>
      </div>

      {/* Log entries */}
      <div ref={scrollRef} className="max-h-80 overflow-y-auto rounded-md border bg-muted/30 p-3">
        <div className="space-y-0.5 font-mono text-xs">
          {filtered.map((entry, i) => (
            <div key={i} className={cn('flex gap-2', levelColors[entry.level] || 'text-muted-foreground')}>
              <span className="shrink-0 text-muted-foreground/60">{entry.ts}</span>
              <span className="shrink-0 uppercase w-12">{entry.level}</span>
              {entry.repo && (
                <span className="shrink-0 font-medium">[{entry.repo}]</span>
              )}
              <span className="break-all">{entry.msg}</span>
            </div>
          ))}
          {filtered.length === 0 && (
            <p className="text-muted-foreground">No entries match filters.</p>
          )}
        </div>
      </div>
    </div>
  )
}
