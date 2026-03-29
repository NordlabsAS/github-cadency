import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useOrgTree } from '@/hooks/useRelationships'
import { useDevelopers } from '@/hooks/useDevelopers'
import ErrorCard from '@/components/ErrorCard'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ChevronDown, ChevronRight, Users, UserX } from 'lucide-react'
import type { OrgTreeNode } from '@/utils/types'

function TreeNode({ node, depth = 0 }: { node: OrgTreeNode; depth?: number }) {
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(depth < 2)
  const hasChildren = node.children.length > 0

  return (
    <div>
      <div
        className="flex items-center gap-2 py-1.5 px-2 rounded-md hover:bg-accent/50 transition-colors group"
        style={{ paddingLeft: `${depth * 24 + 8}px` }}
      >
        {hasChildren ? (
          <button
            className="p-0.5 text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        ) : (
          <span className="w-5" />
        )}
        <button
          className="flex items-center gap-2.5 flex-1 min-w-0 text-left"
          onClick={() => navigate(`/team/${node.developer_id}`)}
        >
          {node.avatar_url ? (
            <img
              src={node.avatar_url}
              alt={node.display_name}
              className="h-8 w-8 rounded-full shrink-0"
            />
          ) : (
            <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center text-sm font-bold shrink-0">
              {node.display_name[0]}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium truncate">{node.display_name}</span>
              <span className="text-xs text-muted-foreground">@{node.github_username}</span>
            </div>
            <div className="flex items-center gap-1.5">
              {node.role && (
                <Badge variant="secondary" className="text-xs h-5">
                  {node.role.replace('_', ' ')}
                </Badge>
              )}
              {node.team && (
                <Badge variant="outline" className="text-xs h-5">
                  {node.team}
                </Badge>
              )}
              {node.office && (
                <span className="text-xs text-muted-foreground">{node.office}</span>
              )}
            </div>
          </div>
          {hasChildren && (
            <Badge variant="secondary" className="text-xs shrink-0">
              {node.children.length} report{node.children.length !== 1 ? 's' : ''}
            </Badge>
          )}
        </button>
      </div>
      {expanded &&
        hasChildren &&
        node.children.map((child) => (
          <TreeNode key={child.developer_id} node={child} depth={depth + 1} />
        ))}
    </div>
  )
}

export default function OrgChart() {
  const [teamFilter, setTeamFilter] = useState('')
  const { data: tree, isLoading, isError, refetch } = useOrgTree(teamFilter || undefined)
  const { data: developers } = useDevelopers()

  const teams = [
    ...new Set((developers ?? []).map((d) => d.team).filter(Boolean)),
  ] as string[]

  if (isError) return <ErrorCard message="Could not load org chart." onRetry={() => refetch()} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Organization Chart</h1>
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
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="pt-6 space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3" style={{ paddingLeft: `${(i % 3) * 24}px` }}>
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="space-y-1.5">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-20" />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : tree ? (
        <>
          {tree.roots.length > 0 && (
            <Card>
              <CardContent className="pt-4 pb-2">
                {tree.roots.map((root) => (
                  <TreeNode key={root.developer_id} node={root} />
                ))}
              </CardContent>
            </Card>
          )}

          {tree.roots.length === 0 && tree.unassigned.length > 0 && (
            <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
              <div className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-400">
                <Users className="h-4 w-4" />
                <span className="font-medium">No reporting relationships configured yet</span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Set "Reports to" relationships on developer profiles to build the org tree.
              </p>
            </div>
          )}

          {tree.unassigned.length > 0 && (
            <div className="space-y-2">
              <h2 className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <UserX className="h-4 w-4" />
                Not in hierarchy ({tree.unassigned.length})
              </h2>
              <Card>
                <CardContent className="pt-4 pb-2">
                  {tree.unassigned.map((node) => (
                    <TreeNode key={node.developer_id} node={node} />
                  ))}
                </CardContent>
              </Card>
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}
