import { useState } from 'react'
import { useAIHistory, useRunAnalysis, useRunOneOnOnePrep, useRunTeamHealth } from '@/hooks/useAI'
import { useDevelopers } from '@/hooks/useDevelopers'
import { useRepos } from '@/hooks/useSync'
import { useDateRange } from '@/hooks/useDateRange'
import ErrorCard from '@/components/ErrorCard'
import TableSkeleton from '@/components/TableSkeleton'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import AnalysisResultRenderer from '@/components/ai/AnalysisResultRenderer'
import type { AIAnalyzeRequest, AIAnalysis as AIAnalysisType } from '@/utils/types'

function HistoryList({
  items,
  emptyMessage,
}: {
  items: AIAnalysisType[]
  emptyMessage: string
}) {
  const [expandedId, setExpandedId] = useState<number | null>(null)

  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyMessage}</p>
  }

  return (
    <div className="space-y-3">
      {items.map((a) => (
        <Card key={a.id}>
          <CardHeader
            className="cursor-pointer pb-2"
            onClick={() => setExpandedId(expandedId === a.id ? null : a.id)}
          >
            <CardTitle className="flex items-center gap-2 text-sm">
              <Badge variant="secondary">{a.analysis_type}</Badge>
              {a.scope_type && a.scope_id && (
                <span className="text-muted-foreground">
                  {a.scope_type}: {a.scope_id}
                </span>
              )}
              <span className="ml-auto text-xs text-muted-foreground">
                {new Date(a.created_at).toLocaleString()}
              </span>
            </CardTitle>
          </CardHeader>
          {expandedId === a.id && (
            <CardContent>
              {a.input_summary && (
                <p className="mb-3 text-sm text-muted-foreground">{a.input_summary}</p>
              )}
              <AnalysisResultRenderer analysisType={a.analysis_type} result={a.result} />
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  )
}

export default function AIAnalysis() {
  const { dateFrom, dateTo } = useDateRange()
  const { data: history, isLoading, isError, refetch } = useAIHistory()
  const runAnalysis = useRunAnalysis()
  const runOneOnOnePrep = useRunOneOnOnePrep()
  const runTeamHealth = useRunTeamHealth()
  const { data: developers } = useDevelopers()
  const { data: repos } = useRepos()

  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<AIAnalyzeRequest>({
    analysis_type: 'communication',
    scope_type: 'developer',
    scope_id: '',
    date_from: '',
    date_to: '',
  })

  // 1:1 prep state
  const [prepDevId, setPrepDevId] = useState('')

  // Team health state
  const [healthTeam, setHealthTeam] = useState('')

  const teams = [...new Set((developers ?? []).map((d) => d.team).filter(Boolean))] as string[]

  const generalTypes = ['communication', 'conflict', 'sentiment']
  const generalHistory = (history ?? []).filter((a) => generalTypes.includes(a.analysis_type ?? ''))
  const prepHistory = (history ?? []).filter((a) => a.analysis_type === 'one_on_one_prep')
  const healthHistory = (history ?? []).filter((a) => a.analysis_type === 'team_health')

  if (isError) {
    return <ErrorCard message="Could not load AI analysis history." onRetry={() => refetch()} />
  }
  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">AI Analysis</h1>
        <TableSkeleton columns={6} rows={4} headers={['Type', 'Scope', 'Date Range', 'Model', 'Tokens', 'Created']} />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">AI Analysis</h1>

      <Tabs defaultValue="general">
        <TabsList>
          <TabsTrigger value="general">General Analysis</TabsTrigger>
          <TabsTrigger value="prep">1:1 Prep</TabsTrigger>
          <TabsTrigger value="health">Team Health</TabsTrigger>
        </TabsList>

        {/* General Analysis Tab */}
        <TabsContent value="general">
          <div className="space-y-4">
            <div className="flex justify-end">
              <Dialog open={open} onOpenChange={setOpen}>
                <DialogTrigger asChild>
                  <Button>New Analysis</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Run AI Analysis</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">Analysis Type</label>
                      <select
                        className="flex h-9 w-full rounded-md border bg-background px-3 py-1 text-sm"
                        value={form.analysis_type}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            analysis_type: e.target.value as AIAnalyzeRequest['analysis_type'],
                          })
                        }
                      >
                        <option value="communication">Communication</option>
                        <option value="conflict">Conflict</option>
                        <option value="sentiment">Sentiment</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">Scope</label>
                      <select
                        className="flex h-9 w-full rounded-md border bg-background px-3 py-1 text-sm"
                        value={form.scope_type}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            scope_type: e.target.value as AIAnalyzeRequest['scope_type'],
                            scope_id: '',
                          })
                        }
                      >
                        <option value="developer">Developer</option>
                        <option value="team">Team</option>
                        <option value="repo">Repository</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">
                        {form.scope_type === 'developer'
                          ? 'Developer'
                          : form.scope_type === 'team'
                            ? 'Team'
                            : 'Repository'}
                      </label>
                      <select
                        className="flex h-9 w-full rounded-md border bg-background px-3 py-1 text-sm"
                        value={form.scope_id}
                        onChange={(e) => setForm({ ...form, scope_id: e.target.value })}
                      >
                        <option value="">Select...</option>
                        {form.scope_type === 'developer' &&
                          (developers ?? []).map((d) => (
                            <option key={d.id} value={String(d.id)}>
                              {d.display_name} (@{d.github_username})
                            </option>
                          ))}
                        {form.scope_type === 'team' &&
                          teams.map((t) => (
                            <option key={t} value={t}>{t}</option>
                          ))}
                        {form.scope_type === 'repo' &&
                          (repos ?? []).map((r) => (
                            <option key={r.id} value={String(r.id)}>
                              {r.full_name}
                            </option>
                          ))}
                      </select>
                    </div>

                    <p className="text-sm text-muted-foreground">
                      Date range: {dateFrom} to {dateTo}
                    </p>

                    <div className="flex justify-end gap-2">
                      <DialogClose asChild>
                        <Button variant="outline">Cancel</Button>
                      </DialogClose>
                      <Button
                        disabled={!form.scope_id || runAnalysis.isPending}
                        onClick={() => {
                          runAnalysis.mutate(
                            {
                              ...form,
                              date_from: new Date(dateFrom).toISOString(),
                              date_to: new Date(dateTo).toISOString(),
                            },
                            { onSuccess: () => setOpen(false) }
                          )
                        }}
                      >
                        {runAnalysis.isPending ? 'Running...' : 'Run Analysis'}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            <HistoryList items={generalHistory} emptyMessage="No general analyses yet. Run one to get started." />
          </div>
        </TabsContent>

        {/* 1:1 Prep Tab */}
        <TabsContent value="prep">
          <div className="space-y-4">
            <Card>
              <CardContent className="flex flex-wrap items-end gap-4 pt-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium">Developer</label>
                  <select
                    className="flex h-9 w-full min-w-[200px] rounded-md border bg-background px-3 py-1 text-sm"
                    value={prepDevId}
                    onChange={(e) => setPrepDevId(e.target.value)}
                  >
                    <option value="">Select developer...</option>
                    {(developers ?? []).map((d) => (
                      <option key={d.id} value={String(d.id)}>
                        {d.display_name} (@{d.github_username})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="text-sm text-muted-foreground">
                  {dateFrom} to {dateTo}
                </div>
                <Button
                  disabled={!prepDevId || runOneOnOnePrep.isPending}
                  onClick={() => {
                    runOneOnOnePrep.mutate({
                      developer_id: Number(prepDevId),
                      date_from: new Date(dateFrom).toISOString(),
                      date_to: new Date(dateTo).toISOString(),
                    })
                  }}
                >
                  {runOneOnOnePrep.isPending ? 'Generating...' : 'Generate Brief'}
                </Button>
              </CardContent>
            </Card>

            <HistoryList items={prepHistory} emptyMessage="No 1:1 prep briefs yet." />
          </div>
        </TabsContent>

        {/* Team Health Tab */}
        <TabsContent value="health">
          <div className="space-y-4">
            <Card>
              <CardContent className="flex flex-wrap items-end gap-4 pt-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium">Team</label>
                  <select
                    className="flex h-9 w-full min-w-[200px] rounded-md border bg-background px-3 py-1 text-sm"
                    value={healthTeam}
                    onChange={(e) => setHealthTeam(e.target.value)}
                  >
                    <option value="">All teams</option>
                    {teams.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div className="text-sm text-muted-foreground">
                  {dateFrom} to {dateTo}
                </div>
                <Button
                  disabled={runTeamHealth.isPending}
                  onClick={() => {
                    runTeamHealth.mutate({
                      ...(healthTeam ? { team: healthTeam } : {}),
                      date_from: new Date(dateFrom).toISOString(),
                      date_to: new Date(dateTo).toISOString(),
                    })
                  }}
                >
                  {runTeamHealth.isPending ? 'Generating...' : 'Generate Assessment'}
                </Button>
              </CardContent>
            </Card>

            <HistoryList items={healthHistory} emptyMessage="No team health assessments yet." />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
